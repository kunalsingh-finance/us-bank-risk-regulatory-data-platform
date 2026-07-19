"""Reproducible, split-assigned Phase 5 model datasets with masked locked outcomes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.database.manifest import JsonObject, sha256_file

from .config import included_features, load_hashed_config, require_string
from .manifest import write_manifest


@dataclass(frozen=True)
class DatasetBuildResult:
    database_path: Path
    database_sha256: str
    split_assignment_sha256: str
    feature_count: int


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def split_case(date_column: str) -> str:
    return (
        f"CASE WHEN {date_column} BETWEEN DATE '2001-03-31' AND DATE '2013-12-31' THEN 'TRAIN' "
        f"WHEN {date_column} BETWEEN DATE '2014-03-31' AND DATE '2018-12-31' THEN 'VALIDATION' "
        f"WHEN {date_column} BETWEEN DATE '2019-03-31' AND DATE '2024-12-31' THEN 'LOCKED_TEST' "
        "ELSE 'OUTSIDE_PROTOCOL' END"
    )


def feature_quality_expression() -> str:
    return (
        "CASE WHEN q.suspected_unit_issue THEN 'BLOCKING' "
        "WHEN q.identifier_continuity_concern OR q.source_field_quality_warning "
        "OR q.peer_group_too_small OR q.extreme_preserved_value THEN 'WARNING' ELSE 'PASS' END"
    )


def create_model_table_sql(
    table_name: str,
    label_table: str,
    outcome: str,
    status_column: str,
    feature_names: tuple[str, ...],
    phase3_hash: str,
    phase4_hash: str,
    protocol_hash: str,
) -> str:
    columns: str = ",\n       ".join(f'f."{name}"' for name in feature_names)
    target: str = f"CASE WHEN f.reporting_date <= DATE '2018-12-31' THEN l.{outcome} END"
    status: str = f"CASE WHEN f.reporting_date <= DATE '2018-12-31' THEN l.{status_column} ELSE 'LOCKED_TEST_MASKED' END"
    return f"""CREATE TABLE core.{table_name} AS
        SELECT f.cert,f.rssdid,f.reporting_date,{split_case('f.reporting_date')} AS split_assignment,
               {target} AS outcome,{status} AS label_eligibility_status,
               p.asset_size_band,COALESCE(p.bank_class,'UNKNOWN') AS bank_class,
               {feature_quality_expression()} AS feature_quality_status,
               {columns},
               '{protocol_hash}' AS experiment_protocol_hash,
               '{phase3_hash}' AS feature_database_sha256,
               '{phase4_hash}' AS label_database_sha256,
               f.feature_configuration_hash,f.feature_build_run_id,l.label_build_run_id
        FROM phase3.core.bank_quarter_risk_features f
        JOIN phase3.core.bank_quarter_feature_quality q USING(cert,rssdid,reporting_date)
        JOIN phase3.core.bank_peer_groups p USING(cert,rssdid,reporting_date)
        JOIN phase4.{label_table} l USING(cert,rssdid,reporting_date)
        WHERE l.{status_column} IN ('POSITIVE','NEGATIVE')
          AND f.reporting_date BETWEEN DATE '2001-03-31' AND DATE '2024-12-31'
        ORDER BY f.reporting_date,f.cert"""


def export_query(connection: duckdb.DuckDBPyConnection, query: str, path: Path) -> str:
    connection.execute(f"COPY ({query}) TO '{sql_path(path)}' (FORMAT CSV, HEADER TRUE)")
    return sha256_file(path)


def build_model_datasets(root: Path) -> DatasetBuildResult:
    protocol: JsonObject = load_hashed_config(root / "configs/experiment_protocol.yaml")
    features: JsonObject = load_hashed_config(root / "configs/model_features.yaml")
    names: tuple[str, ...] = included_features(features)
    phase3_path: Path = root / "database/bank_risk_features.duckdb"
    phase4_path: Path = root / "database/bank_risk_labels.duckdb"
    for path, key in ((phase3_path,"phase3_database_sha256"),(phase4_path,"phase4_database_sha256")):
        observed: str = sha256_file(path)
        expected: str = require_string(protocol,key)
        if observed != expected:
            raise ValueError(f"Immutable model input mismatch: path={path}, expected={expected}, observed={observed}")
    output_path: Path = root / "database/bank_risk_models.duckdb"
    temporary_path: Path = output_path.with_name(".bank_risk_models.phase5.tmp.duckdb")
    if temporary_path.exists():
        temporary_path.unlink()
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(temporary_path))
    connection.execute(f"ATTACH '{sql_path(phase3_path)}' AS phase3 (READ_ONLY)")
    connection.execute(f"ATTACH '{sql_path(phase4_path)}' AS phase4 (READ_ONLY)")
    connection.execute("CREATE SCHEMA core; CREATE SCHEMA modeling")
    protocol_hash: str = require_string(protocol,"configuration_hash")
    phase3_hash: str = require_string(protocol,"phase3_database_sha256")
    phase4_hash: str = require_string(protocol,"phase4_database_sha256")
    specifications: tuple[tuple[str,str,str,str], ...] = (
        ("model_dataset_failure_4q","core.bank_quarter_failure_labels","failed_within_4_quarters","failure_label_status_4q"),
        ("model_dataset_failure_8q","core.bank_quarter_failure_labels","failed_within_8_quarters","failure_label_status_8q"),
        ("model_dataset_deterioration_4q","core.bank_quarter_distress_labels","severe_deterioration_within_4_quarters","distress_label_status"),
    )
    for table_name,label_table,outcome,status_column in specifications:
        connection.execute(create_model_table_sql(table_name,label_table,outcome,status_column,names,phase3_hash,phase4_hash,protocol_hash))
    connection.execute("""CREATE TABLE modeling.split_assignments AS
        SELECT cert,rssdid,reporting_date,split_assignment FROM core.model_dataset_failure_4q
        ORDER BY reporting_date,cert""")
    connection.execute("""CREATE TABLE modeling.experiment_protocol (
        protocol_hash VARCHAR PRIMARY KEY, protocol_version VARCHAR, frozen_at TIMESTAMP,
        feature_contract_hash VARCHAR, candidate_contract_hash VARCHAR, metric_contract_hash VARCHAR,
        locked_test_policy_hash VARCHAR, status VARCHAR)""")
    connection.execute("INSERT INTO modeling.experiment_protocol VALUES (?,?,?::TIMESTAMP,?,?,?,?,'FROZEN')",[
        protocol_hash,require_string(protocol,"version"),require_string(protocol,"freeze_timestamp"),
        require_string(protocol,"model_features_hash"),require_string(protocol,"model_candidates_hash"),
        require_string(protocol,"evaluation_metrics_hash"),require_string(protocol,"locked_test_policy_hash")])
    connection.execute("""CREATE TABLE modeling.dataset_registry (
        dataset_name VARCHAR,rows BIGINT,train_rows BIGINT,validation_rows BIGINT,locked_rows BIGINT,
        positive_train BIGINT,positive_validation BIGINT,locked_targets_masked BIGINT,protocol_hash VARCHAR)""")
    for table_name,_,_,_ in specifications:
        connection.execute(f"""INSERT INTO modeling.dataset_registry SELECT '{table_name}',COUNT(*),
            COUNT(*) FILTER(WHERE split_assignment='TRAIN'),COUNT(*) FILTER(WHERE split_assignment='VALIDATION'),
            COUNT(*) FILTER(WHERE split_assignment='LOCKED_TEST'),
            COUNT(*) FILTER(WHERE split_assignment='TRAIN' AND outcome=1),
            COUNT(*) FILTER(WHERE split_assignment='VALIDATION' AND outcome=1),
            COUNT(*) FILTER(WHERE split_assignment='LOCKED_TEST' AND outcome IS NULL),'{protocol_hash}'
            FROM core.{table_name}""")
    connection.execute("""CREATE TABLE modeling.model_registry (
        model_id VARCHAR, outcome_name VARCHAR, family VARCHAR, parameters_json VARCHAR,
        artifact_path VARCHAR, artifact_sha256 VARCHAR, selected BOOLEAN, protocol_hash VARCHAR)""")
    connection.execute("""CREATE TABLE modeling.training_runs (
        run_id VARCHAR,model_id VARCHAR,outcome_name VARCHAR,fold VARCHAR,train_start DATE,train_end DATE,
        evaluation_start DATE,evaluation_end DATE,train_rows BIGINT,train_positives BIGINT,status VARCHAR)""")
    connection.execute("""CREATE TABLE modeling.validation_predictions (
        cert BIGINT,rssdid BIGINT,reporting_date DATE,outcome_name VARCHAR,model_id VARCHAR,target INTEGER,
        raw_probability DOUBLE,probability DOUBLE,asset_size_band VARCHAR,bank_class VARCHAR,
        feature_quality_status VARCHAR,protocol_hash VARCHAR)""")
    connection.execute("""CREATE TABLE modeling.locked_test_predictions AS SELECT * FROM modeling.validation_predictions WHERE FALSE""")
    connection.execute("""CREATE TABLE modeling.model_metrics (
        outcome_name VARCHAR,model_id VARCHAR,split VARCHAR,metric_name VARCHAR,metric_value DOUBLE,protocol_hash VARCHAR)""")
    connection.execute("""CREATE TABLE modeling.calibration_results (
        outcome_name VARCHAR,model_id VARCHAR,method VARCHAR,evaluation_period VARCHAR,brier_score DOUBLE,
        calibration_intercept DOUBLE,calibration_slope DOUBLE,ece DOUBLE,selected BOOLEAN)""")
    connection.execute("""CREATE TABLE modeling.failure_event_capture (
        cert BIGINT,failure_date DATE,maximum_pre_failure_score DOUBLE,captured_top_1pct BOOLEAN,
        captured_top_5pct BOOLEAN,captured_top_10pct BOOLEAN,earliest_alert_top_5pct DATE,lead_days_top_5pct BIGINT)""")
    connection.execute("""CREATE TABLE modeling.feature_importance (
        outcome_name VARCHAR,model_id VARCHAR,feature_name VARCHAR,importance_type VARCHAR,
        importance_value DOUBLE,importance_std DOUBLE)""")
    connection.execute("""CREATE TABLE modeling.threshold_results (
        outcome_name VARCHAR,model_id VARCHAR,split VARCHAR,threshold_type VARCHAR,threshold_value DOUBLE,
        alert_budget DOUBLE,precision DOUBLE,recall DOUBLE,alerts BIGINT,false_alerts BIGINT)""")
    report_dir: Path = root / "reports"
    report_dir.mkdir(parents=True,exist_ok=True)
    reconciliation_hash: str = export_query(connection,"""SELECT dataset_name,rows,train_rows,validation_rows,locked_rows,
        positive_train,positive_validation,locked_targets_masked,
        CASE WHEN rows=train_rows+validation_rows+locked_rows AND locked_rows=locked_targets_masked THEN 'PASS' ELSE 'FAIL' END status
        FROM modeling.dataset_registry ORDER BY dataset_name""",report_dir/"model_dataset_reconciliation.csv")
    split_hash: str = export_query(connection,"SELECT * FROM modeling.split_assignments ORDER BY reporting_date,cert",report_dir/"split_assignments.csv")
    diagnostics: pd.DataFrame = connection.execute("""SELECT dataset_name,split_assignment,COUNT(*) observations,
        COUNT(outcome) labelled_observations,SUM(COALESCE(outcome,0)) positives,COUNT(DISTINCT cert) institutions,
        MIN(reporting_date) first_date,MAX(reporting_date) last_date
        FROM (SELECT 'failure_4q' dataset_name,* FROM core.model_dataset_failure_4q
              UNION ALL BY NAME SELECT 'failure_8q',* FROM core.model_dataset_failure_8q
              UNION ALL BY NAME SELECT 'deterioration_4q',* FROM core.model_dataset_deterioration_4q)
        GROUP BY dataset_name,split_assignment ORDER BY dataset_name,split_assignment""").fetch_df()
    diagnostics.to_csv(report_dir/"split_diagnostics.csv",index=False,lineterminator="\n")
    overlap: pd.DataFrame = connection.execute("""WITH s AS (SELECT DISTINCT cert,split_assignment FROM modeling.split_assignments)
        SELECT a.split_assignment first_split,b.split_assignment second_split,COUNT(DISTINCT a.cert) shared_institutions
        FROM s a JOIN s b USING(cert) WHERE a.split_assignment < b.split_assignment GROUP BY 1,2 ORDER BY 1,2""").fetch_df()
    overlap.to_csv(report_dir/"institution_overlap_by_split.csv",index=False,lineterminator="\n")
    events: pd.DataFrame = connection.execute("""SELECT CASE WHEN closing_date<=DATE '2013-12-31' THEN 'TRAIN'
        WHEN closing_date<=DATE '2018-12-31' THEN 'VALIDATION' WHEN closing_date<=DATE '2024-12-31' THEN 'LOCKED_TEST' ELSE 'OUTSIDE'
        END split_assignment,COUNT(*) unique_failure_events,MIN(closing_date) first_event,MAX(closing_date) last_event
        FROM phase4.core.validated_failure_events WHERE validation_status='VALIDATED' GROUP BY 1 ORDER BY 1""").fetch_df()
    events.to_csv(report_dir/"failure_events_by_split.csv",index=False,lineterminator="\n")
    folds: object = protocol["cross_validation"]
    if not isinstance(folds,dict) or not isinstance(folds.get("folds"),list):
        raise TypeError("Invalid cross-validation configuration")
    fold_rows: list[dict[str,object]] = []
    for raw in folds["folds"]:
        if not isinstance(raw,dict):
            raise TypeError("Invalid fold")
        train_dates: list[object] = raw["train"]
        validation_dates: list[object] = raw["validation"]
        query: str = """SELECT COUNT(*) FILTER(WHERE reporting_date BETWEEN ?::DATE AND ?::DATE),
            COUNT(*) FILTER(WHERE reporting_date BETWEEN ?::DATE AND ?::DATE AND outcome=1),
            COUNT(*) FILTER(WHERE reporting_date BETWEEN ?::DATE AND ?::DATE),
            COUNT(*) FILTER(WHERE reporting_date BETWEEN ?::DATE AND ?::DATE AND outcome=1)
            FROM core.model_dataset_failure_4q"""
        values: tuple[object,...] = tuple(connection.execute(query,[train_dates[0],train_dates[1],train_dates[0],train_dates[1],validation_dates[0],validation_dates[1],validation_dates[0],validation_dates[1]]).fetchone())
        fold_rows.append({"fold":raw["fold"],"train_start":train_dates[0],"train_end":train_dates[1],"validation_start":validation_dates[0],"validation_end":validation_dates[1],"train_rows":values[0],"train_positives":values[1],"validation_rows":values[2],"validation_positives":values[3]})
    pd.DataFrame(fold_rows).to_csv(report_dir/"cross_validation_folds.csv",index=False,lineterminator="\n")
    pd.DataFrame([{"control":"preprocessing_fit","status":"NOT_FITTED_AT_DATASET_BUILD","evidence":"Raw features and masked test targets only"}]).to_csv(report_dir/"preprocessing_audit.csv",index=False,lineterminator="\n")
    connection.close()
    os.replace(temporary_path,output_path)
    database_hash: str = sha256_file(output_path)
    manifest: JsonObject = {"status":"PASS","protocol_hash":protocol_hash,"feature_count":len(names),
        "database_sha256":database_hash,"split_assignment_sha256":split_hash,"reconciliation_sha256":reconciliation_hash,
        "phase3_database_sha256":phase3_hash,"phase4_database_sha256":phase4_hash}
    write_manifest(root/"manifests/model_experiment/dataset_manifest.json",manifest)
    return DatasetBuildResult(output_path,database_hash,split_hash,len(names))
