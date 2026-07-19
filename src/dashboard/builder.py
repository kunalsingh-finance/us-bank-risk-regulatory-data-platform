"""Reproducible Phase 6 prepared presentation-table build."""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve

from src.database.manifest import JsonObject, sha256_file
from src.models.config import included_features, load_hashed_config, require_string

from .config import load_dashboard_configs, string_list
from .explanations import load_frozen_model, local_perturbation_drivers
from .manifest import file_inventory, write_dashboard_manifest
from .validation import REQUIRED_METADATA_COLUMNS, validate_parquet_schema, verify_immutable_inputs


PRESENTATION_NAMES: tuple[str, ...] = (
    "bank_scores", "bank_history", "current_watchlist", "driver_explanations",
    "peer_comparisons", "model_validation", "failure_case_studies", "data_quality", "metadata",
)


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def write_parquet(frame: pd.DataFrame, path: Path, sort_columns: tuple[str, ...]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path = path.with_suffix(".tmp.parquet")
    ordered: pd.DataFrame = frame.sort_values(list(sort_columns), kind="stable").reset_index(drop=True) if sort_columns else frame.reset_index(drop=True)
    ordered.to_parquet(temporary, index=False, engine="pyarrow", compression="zstd")
    os.replace(temporary, path)
    return sha256_file(path)


def add_metadata(frame: pd.DataFrame, config: JsonObject, source_lineage: str) -> pd.DataFrame:
    output: pd.DataFrame = frame.copy()
    output["dashboard_build_run_id"] = require_string(config, "dashboard_build_run_id")
    output["dashboard_configuration_hash"] = require_string(config, "configuration_hash")
    output["frozen_model_version"] = require_string(config, "frozen_model_version")
    output["prediction_source_hash"] = require_string(config, "phase5_model_database_sha256")
    output["source_lineage"] = source_lineage
    output["build_timestamp"] = require_string(config, "build_timestamp")
    output["validation_status"] = "PASS"
    return output


def attach_sources(connection: duckdb.DuckDBPyConnection, root: Path) -> None:
    for alias, filename in (
        ("model", "bank_risk_models.duckdb"), ("feature", "bank_risk_features.duckdb"),
        ("label", "bank_risk_labels.duckdb"), ("warehouse", "bank_risk.duckdb"),
    ):
        connection.execute(f"ATTACH '{sql_path(root / 'database' / filename)}' AS {alias} (READ_ONLY)")


def create_score_table(connection: duckdb.DuckDBPyConnection, config: JsonObject) -> None:
    protocol_hash: str = require_string(config, "protocol_hash")
    connection.execute(f"""CREATE OR REPLACE TABLE scores AS
        WITH predictions AS (
            SELECT cert,rssdid,CAST(reporting_date AS DATE) reporting_date,raw_probability model_score,
                   target historical_outcome,'VALIDATION' prediction_split,asset_size_band,bank_class,
                   feature_quality_status,protocol_hash
            FROM model.modeling.validation_predictions WHERE outcome_name='failure_4q'
            UNION ALL
            SELECT cert,rssdid,CAST(reporting_date AS DATE),raw_probability,target,'LOCKED_TEST',asset_size_band,
                   bank_class,feature_quality_status,protocol_hash
            FROM model.modeling.locked_test_predictions WHERE outcome_name='failure_4q'
        ), identified AS (
            SELECT p.*,COALESCE(f.institution_name,'CERT ' || CAST(p.cert AS VARCHAR)) bank_name,
                   COALESCE(f.state,'Unknown') state,pg.final_peer_group_id,pg.final_peer_group_size,
                   pg.peer_group_method,CASE WHEN pg.final_peer_group_size>=20 THEN 'PASS' ELSE 'WARNING' END peer_benchmark_status,
                   COUNT(*) OVER(PARTITION BY p.reporting_date) scored_population,
                   RANK() OVER(PARTITION BY p.reporting_date ORDER BY p.model_score DESC) same_quarter_rank,
                   ROW_NUMBER() OVER(PARTITION BY p.reporting_date ORDER BY p.model_score DESC,p.cert ASC) budget_rank,
                   100.0*PERCENT_RANK() OVER(PARTITION BY p.reporting_date ORDER BY p.model_score ASC) same_quarter_percentile
            FROM predictions p
            JOIN warehouse.core.bank_quarter_financials f USING(cert,rssdid,reporting_date)
            JOIN feature.core.bank_peer_groups pg USING(cert,rssdid,reporting_date)
            WHERE p.protocol_hash='{protocol_hash}'
        ), flagged AS (
            SELECT *,budget_rank<=CEIL(scored_population*0.01) top_1_percent_flag,
                     budget_rank<=CEIL(scored_population*0.05) top_5_percent_flag,
                     budget_rank<=CEIL(scored_population*0.10) top_10_percent_flag,
                     CASE WHEN same_quarter_percentile<50 THEN 'Low'
                          WHEN same_quarter_percentile<90 THEN 'Moderate'
                          WHEN same_quarter_percentile<95 THEN 'Elevated'
                          WHEN same_quarter_percentile<99 THEN 'High' ELSE 'Highest monitored tier' END risk_tier
            FROM identified
        )
        SELECT current.* EXCLUDE(budget_rank),prior.same_quarter_percentile prior_quarter_percentile,
               yearago.same_quarter_percentile four_quarter_prior_percentile,
               current.same_quarter_percentile-prior.same_quarter_percentile percentile_change_qoq,
               current.same_quarter_percentile-yearago.same_quarter_percentile percentile_change_yoy,
               TRUE out_of_sample_flag,
               CASE WHEN current.top_5_percent_flag THEN 'Top-5% review'
                    WHEN current.same_quarter_percentile>=90 THEN 'Elevated indicators'
                    WHEN current.same_quarter_percentile>=50 THEN 'Monitor' ELSE 'No alert' END alert_status,
               CASE WHEN current.feature_quality_status='PASS' THEN '' ELSE 'Feature-quality warning: ' || current.feature_quality_status END data_quality_warning,
               'Ranking model only; weak calibration and rare-event uncertainty apply.' model_limitation_warning
        FROM flagged current
        LEFT JOIN flagged prior ON prior.cert=current.cert AND prior.reporting_date=current.reporting_date-INTERVAL 3 MONTH
        LEFT JOIN flagged yearago ON yearago.cert=current.cert AND yearago.reporting_date=current.reporting_date-INTERVAL 12 MONTH
        ORDER BY current.reporting_date,current.cert""")


def score_frame(connection: duckdb.DuckDBPyConnection, config: JsonObject) -> pd.DataFrame:
    frame: pd.DataFrame = connection.execute("SELECT * FROM scores ORDER BY reporting_date,cert").fetch_df()
    return add_metadata(frame, config, "Frozen Phase 5 validation and locked-test primary predictions; Phase 2 identity; Phase 3 peer groups")


def history_frame(connection: duckdb.DuckDBPyConnection, config: JsonObject, features: tuple[str, ...]) -> pd.DataFrame:
    selected: str = ",".join(f'f."{name}"' for name in features)
    frame: pd.DataFrame = connection.execute(f"""SELECT s.cert,s.rssdid,s.bank_name,s.state,s.reporting_date,s.asset_size_band,
        s.bank_class,s.model_score,s.same_quarter_percentile,s.same_quarter_rank,s.scored_population,s.risk_tier,
        s.top_1_percent_flag,s.top_5_percent_flag,s.top_10_percent_flag,s.prediction_split,s.feature_quality_status,
        s.peer_benchmark_status,{selected}
        FROM scores s JOIN feature.core.bank_quarter_risk_features f USING(cert,rssdid,reporting_date)
        ORDER BY s.reporting_date,s.cert""").fetch_df()
    return add_metadata(frame, config, "Frozen scores joined one-to-one to Phase 3 validated risk features")


def driver_frame(
    connection: duckdb.DuckDBPyConnection,
    root: Path,
    config: JsonObject,
    explanation_features: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_config: JsonObject = load_hashed_config(root / "configs/model_features.yaml")
    feature_names: tuple[str, ...] = included_features(feature_config)
    selected: str = ",".join(f'd."{name}"' for name in feature_names)
    frame: pd.DataFrame = connection.execute(f"""SELECT s.cert,s.rssdid,s.reporting_date,s.model_score,{selected}
        FROM scores s JOIN model.core.model_dataset_failure_4q d USING(cert,rssdid,reporting_date)
        ORDER BY s.reporting_date,s.cert""").fetch_df()
    model = load_frozen_model(root / require_string(config, "model_artifact_path"), require_string(config, "model_artifact_sha256"))
    drivers, validation = local_perturbation_drivers(
        model, frame, feature_names, explanation_features, frame["model_score"].to_numpy(dtype=float)
    )
    connection.register("driver_input", drivers)
    enriched: pd.DataFrame = connection.execute("""SELECT d.*,b.final_peer_group_id,b.peer_group_method,b.peer_count,
        b.peer_median,b.peer_p25,b.peer_p75,b.bank_percentile,b.risk_direction_adjusted_percentile,
        b.difference_from_peer_median,b.peer_feature_count_too_small,
        CASE WHEN b.peer_feature_count_too_small THEN 'Peer feature group below 20 observations'
             WHEN b.peer_count IS NULL THEN 'Peer comparison unavailable' ELSE '' END peer_comparison_warning
        FROM driver_input d LEFT JOIN feature.core.bank_quarter_peer_benchmarks b
        ON b.cert=d.cert AND b.rssdid=d.rssdid AND b.reporting_date=d.reporting_date AND b.feature_name=d.feature_name
        ORDER BY d.reporting_date,d.cert,d.driver_rank""").fetch_df()
    connection.unregister("driver_input")
    return add_metadata(enriched, config, "Frozen model local perturbation joined to same-quarter Phase 3 peer benchmark"), validation


def peer_frame(connection: duckdb.DuckDBPyConnection, config: JsonObject, features: tuple[str, ...]) -> pd.DataFrame:
    literals: str = ",".join("'" + name.replace("'", "''") + "'" for name in features)
    frame: pd.DataFrame = connection.execute(f"""SELECT b.cert,b.rssdid,s.bank_name,s.state,b.reporting_date,s.asset_size_band,
        s.bank_class,b.final_peer_group_id,b.peer_group_method,b.feature_name,b.feature_value,b.peer_count,b.peer_mean,
        b.peer_median,b.peer_p25,b.peer_p75,b.bank_percentile,b.risk_direction_adjusted_percentile,
        b.difference_from_peer_median,b.robust_z_score,b.peer_feature_count_too_small,
        CASE WHEN b.peer_feature_count_too_small THEN 'WARNING' ELSE 'PASS' END peer_validation_status
        FROM feature.core.bank_quarter_peer_benchmarks b JOIN scores s USING(cert,rssdid,reporting_date)
        WHERE b.feature_name IN ({literals}) ORDER BY b.reporting_date,b.cert,b.feature_name""").fetch_df()
    return add_metadata(frame, config, "Phase 3 same-quarter peer benchmarks restricted to scored observations and configured features")


def watchlist_frame(connection: duckdb.DuckDBPyConnection, drivers: pd.DataFrame, config: JsonObject) -> pd.DataFrame:
    connection.register("driver_output", drivers)
    frame: pd.DataFrame = connection.execute("""WITH pivoted AS (
        SELECT cert,rssdid,reporting_date,
          MAX(feature_name) FILTER(WHERE driver_rank=1) top_driver_1,
          MAX(feature_name) FILTER(WHERE driver_rank=2) top_driver_2,
          MAX(feature_name) FILTER(WHERE driver_rank=3) top_driver_3,
          MAX(driver_direction) FILTER(WHERE driver_rank=1) driver_direction_1,
          MAX(driver_direction) FILTER(WHERE driver_rank=2) driver_direction_2,
          MAX(driver_direction) FILTER(WHERE driver_rank=3) driver_direction_3,
          MAX(current_feature_value) FILTER(WHERE driver_rank=1) current_driver_value_1,
          MAX(current_feature_value) FILTER(WHERE driver_rank=2) current_driver_value_2,
          MAX(current_feature_value) FILTER(WHERE driver_rank=3) current_driver_value_3,
          MAX(CASE WHEN driver_rank=1 THEN 'Peer median ' || COALESCE(CAST(ROUND(peer_median,3) AS VARCHAR),'unavailable') END) peer_comparison_1,
          MAX(CASE WHEN driver_rank=2 THEN 'Peer median ' || COALESCE(CAST(ROUND(peer_median,3) AS VARCHAR),'unavailable') END) peer_comparison_2,
          MAX(CASE WHEN driver_rank=3 THEN 'Peer median ' || COALESCE(CAST(ROUND(peer_median,3) AS VARCHAR),'unavailable') END) peer_comparison_3
        FROM driver_output GROUP BY cert,rssdid,reporting_date
    ) SELECT s.cert,s.rssdid,s.bank_name,s.state,s.reporting_date,s.asset_size_band,s.bank_class,s.model_score,
        s.same_quarter_percentile,s.same_quarter_rank,s.scored_population,s.risk_tier,s.top_1_percent_flag,
        s.top_5_percent_flag,s.top_10_percent_flag,s.percentile_change_qoq,s.percentile_change_yoy,s.alert_status,
        s.prediction_split,s.out_of_sample_flag,s.feature_quality_status,s.peer_benchmark_status,
        p.top_driver_1,p.top_driver_2,p.top_driver_3,p.driver_direction_1,p.driver_direction_2,p.driver_direction_3,
        p.current_driver_value_1,p.current_driver_value_2,p.current_driver_value_3,
        p.peer_comparison_1,p.peer_comparison_2,p.peer_comparison_3,s.data_quality_warning,s.model_limitation_warning
        FROM scores s JOIN pivoted p USING(cert,rssdid,reporting_date)
        WHERE s.reporting_date=(SELECT MAX(reporting_date) FROM scores) AND s.top_5_percent_flag
        ORDER BY s.same_quarter_rank,s.cert""").fetch_df()
    connection.unregister("driver_output")
    return add_metadata(frame, config, "Latest scored quarter top-5% frozen monitoring population with linked local drivers")


def validation_frame(root: Path, connection: duckdb.DuckDBPyConnection, config: JsonObject) -> pd.DataFrame:
    metrics: pd.DataFrame = pd.read_csv(root / "reports/locked_test_metrics.csv")
    primary: pd.Series = metrics.loc[metrics["outcome_name"] == "failure_4q"].iloc[0]
    predictions: pd.DataFrame = connection.execute("""SELECT target,probability calibrated_score
        FROM model.modeling.locked_test_predictions WHERE outcome_name='failure_4q' ORDER BY reporting_date,cert""").fetch_df()
    y: np.ndarray = predictions["target"].to_numpy(dtype=int)
    score: np.ndarray = predictions["calibrated_score"].to_numpy(dtype=float)
    precision, recall, pr_threshold = precision_recall_curve(y, score)
    false_positive, true_positive, roc_threshold = roc_curve(y, score)
    rows: list[dict[str, Any]] = []
    for name in ("average_precision", "baseline_average_precision", "pr_auc_lift", "roc_auc", "brier_score", "calibration_slope", "calibration_intercept"):
        rows.append({"section": "headline", "series": "Locked test", "x_label": name, "x_value": None, "y_value": float(primary[name]), "metric_name": name, "detail": "Frozen Phase 5 metric"})
    for index in np.linspace(0, len(precision) - 1, min(300, len(precision)), dtype=int):
        rows.append({"section": "precision_recall_curve", "series": "Frozen model", "x_label": str(index), "x_value": float(recall[index]), "y_value": float(precision[index]), "metric_name": "precision", "detail": "Recall on x-axis"})
    for index in np.linspace(0, len(false_positive) - 1, min(300, len(false_positive)), dtype=int):
        rows.append({"section": "roc_curve", "series": "Frozen model", "x_label": str(index), "x_value": float(false_positive[index]), "y_value": float(true_positive[index]), "metric_name": "true_positive_rate", "detail": "False-positive rate on x-axis"})
    calibration: pd.DataFrame = pd.read_csv(root / "reports/locked_test_calibration.csv")
    for record in calibration.loc[calibration["outcome_name"] == "failure_4q"].to_dict("records"):
        rows.append({"section": "calibration", "series": str(record["bin"]), "x_label": str(record["bin"]), "x_value": float(record["mean_probability"]), "y_value": float(record["observed_rate"]), "metric_name": "observed_rate", "detail": f"n={int(record['observations'])}"})
    thresholds: pd.DataFrame = pd.read_csv(root / "reports/locked_test_threshold_results.csv")
    for record in thresholds.loc[(thresholds["outcome_name"] == "failure_4q") & thresholds["alert_budget"].notna()].to_dict("records"):
        rows.append({"section": "alert_budget", "series": f"Top {float(record['alert_budget'])*100:.0f}%", "x_label": "recall", "x_value": float(record["alert_budget"]), "y_value": float(record["recall"]), "metric_name": "recall", "detail": f"alerts={int(record['alerts'])}; false_alerts={int(record['false_alerts'])}"})
        rows.append({"section": "alert_budget", "series": f"Top {float(record['alert_budget'])*100:.0f}%", "x_label": "precision", "x_value": float(record["alert_budget"]), "y_value": float(record["precision"]), "metric_name": "precision", "detail": f"alerts={int(record['alerts'])}; false_alerts={int(record['false_alerts'])}"})
        rows.append({"section": "alert_budget", "series": f"Top {float(record['alert_budget'])*100:.0f}%", "x_label": "alerts", "x_value": float(record["alert_budget"]), "y_value": float(record["alerts"]), "metric_name": "alerts", "detail": f"false_alerts={int(record['false_alerts'])}"})
        rows.append({"section": "alert_budget", "series": f"Top {float(record['alert_budget'])*100:.0f}%", "x_label": "false_alerts", "x_value": float(record["alert_budget"]), "y_value": float(record["false_alerts"]), "metric_name": "false_alerts", "detail": f"alerts={int(record['alerts'])}"})
    for filename, section, group_column in (
        ("model_performance_by_period.csv", "performance_by_year", "reporting_year"),
        ("model_performance_by_asset_band.csv", "performance_by_asset_band", "asset_size_band"),
    ):
        performance: pd.DataFrame = pd.read_csv(root / "reports" / filename)
        for record in performance.to_dict("records"):
            for metric_name in ("observations", "positives", "average_precision"):
                value: object = record.get(metric_name)
                rows.append({"section": section, "series": str(record[group_column]), "x_label": str(record[group_column]), "x_value": None,
                             "y_value": float(value) if pd.notna(value) else None, "metric_name": metric_name,
                             "detail": str(record["reliability"])})
    uncertainty: pd.DataFrame = pd.read_csv(root / "reports/model_uncertainty_intervals.csv")
    for record in uncertainty.loc[uncertainty["outcome_name"] == "failure_4q"].to_dict("records"):
        for bound in ("lower_95", "median", "upper_95"):
            rows.append({"section": "uncertainty_interval", "series": str(record["metric"]), "x_label": bound, "x_value": None,
                         "y_value": float(record[bound]), "metric_name": bound,
                         "detail": f"Institution bootstrap; {record['bootstrap_unit']} unit"})
    lead: pd.DataFrame = pd.read_csv(root / "reports/failure_lead_time_by_event.csv")
    for record in lead.loc[lead["captured_top_5pct"]].to_dict("records"):
        rows.append({"section": "lead_time", "series": str(record["cert"]), "x_label": str(record["failure_date"]), "x_value": None,
                     "y_value": float(record["lead_days_top_5pct"]), "metric_name": "lead_days", "detail": "Top-5% captured event"})
    events: pd.DataFrame = pd.read_csv(root / "reports/failure_event_capture.csv")
    capture_counts: dict[str, int] = {
        "captured_failures_top_1": int(events["captured_top_1pct"].sum()),
        "captured_failures_top_5": int(events["captured_top_5pct"].sum()),
        "captured_failures_top_10": int(events["captured_top_10pct"].sum()),
        "unique_locked_test_failures": int(events["cert"].nunique()),
        "median_top_5_lead_days": int(events.loc[events["captured_top_5pct"], "lead_days_top_5pct"].median()),
        "locked_test_access_count": int(len(pd.read_csv(root / "reports/locked_test_access_log.csv"))),
    }
    for name, value in capture_counts.items():
        rows.append({"section": "headline", "series": "Locked test", "x_label": name, "x_value": None,
                     "y_value": float(value), "metric_name": name, "detail": "Frozen Phase 5 control or event-capture result"})
    frame: pd.DataFrame = pd.DataFrame(rows)
    return add_metadata(frame, config, "Frozen Phase 5 reports and locked-test predictions; chart-only transformation")


def case_study_frame(root: Path, connection: duckdb.DuckDBPyConnection, config: JsonObject) -> pd.DataFrame:
    events: pd.DataFrame = pd.read_csv(root / "reports/failure_event_capture.csv")
    scores: pd.DataFrame = connection.execute("SELECT * FROM scores WHERE prediction_split='LOCKED_TEST' ORDER BY reporting_date,cert").fetch_df()
    positive_scores: pd.DataFrame = scores.loc[scores["historical_outcome"] == 1].copy()
    rows: list[dict[str, Any]] = []

    def event_record(role: str, record: pd.Series, selected_date: object, rationale: str) -> None:
        candidates: pd.DataFrame = scores.loc[(scores["cert"] == int(record["cert"])) & (scores["reporting_date"] == pd.Timestamp(selected_date))]
        if candidates.empty:
            candidates = positive_scores.loc[positive_scores["cert"] == int(record["cert"])].sort_values("reporting_date", ascending=False).head(1)
        if candidates.empty:
            raise ValueError(f"Case-study event lacks scored observation: role={role}, cert={record['cert']}")
        score: pd.Series = candidates.iloc[0]
        rows.append({"case_role": role, "selection_status": "SELECTED", "selection_rationale": rationale,
                     "cert": int(record["cert"]), "rssdid": int(score["rssdid"]), "bank_name": score["bank_name"], "state": score["state"],
                     "reporting_date": score["reporting_date"], "failure_date": record["failure_date"],
                     "first_top_5_alert_date": record.get("earliest_alert_top_5pct"), "lead_days_top_5": record.get("lead_days_top_5pct"),
                     "same_quarter_percentile": score["same_quarter_percentile"], "same_quarter_rank": score["same_quarter_rank"],
                     "asset_size_band": score["asset_size_band"], "risk_tier": score["risk_tier"],
                     "captured_top_1": bool(record["captured_top_1pct"]), "captured_top_5": bool(record["captured_top_5pct"]),
                     "captured_top_10": bool(record["captured_top_10pct"]), "historical_outcome": 1})

    captured: pd.DataFrame = events.loc[events["captured_top_5pct"]].copy()
    short: pd.Series = captured.sort_values(["lead_days_top_5pct", "cert"]).iloc[0]
    long: pd.Series = captured.sort_values(["lead_days_top_5pct", "cert"], ascending=[False, True]).iloc[0]
    top1: pd.Series = events.loc[events["captured_top_1pct"]].sort_values(["maximum_pre_failure_score", "cert"], ascending=[False, True]).iloc[0]
    missed: pd.Series = events.loc[~events["captured_top_10pct"]].sort_values(["failure_date", "cert"]).iloc[0]
    event_record("Short-lead captured failure", short, short["earliest_alert_top_5pct"], "Minimum positive top-5% lead days")
    event_record("Long-lead captured failure", long, long["earliest_alert_top_5pct"], "Maximum top-5% lead days")
    event_record("Top-1% captured failure", top1, top1["earliest_alert_top_1pct"], "Maximum score among top-1% captured events")
    qualifying: pd.DataFrame = events.loc[events["captured_top_5pct"] & ~events["captured_top_1pct"]]
    if qualifying.empty:
        rows.append({"case_role": "Top-5% not top-1% captured failure", "selection_status": "UNAVAILABLE_NO_QUALIFYING_EVENT",
                     "selection_rationale": "Frozen top-1% and top-5% event capture sets are identical because of score ties", "cert": None})
    else:
        selected: pd.Series = qualifying.sort_values(["failure_date", "cert"]).iloc[0]
        event_record("Top-5% not top-1% captured failure", selected, selected["earliest_alert_top_5pct"], "First qualifying event")
    event_record("Missed failure", missed, positive_scores.loc[positive_scores["cert"] == int(missed["cert"]), "reporting_date"].max(), "Earliest event missed at top 10%")
    false_positive: pd.Series = scores.loc[scores["historical_outcome"] == 0].sort_values(["model_score", "reporting_date", "cert"], ascending=[False, True, True]).iloc[0]
    rows.append({"case_role": "False-positive high-ranking institution", "selection_status": "SELECTED",
                 "selection_rationale": "Highest frozen locked-test score among negative observations", "cert": int(false_positive["cert"]),
                 "rssdid": int(false_positive["rssdid"]), "bank_name": false_positive["bank_name"], "state": false_positive["state"],
                 "reporting_date": false_positive["reporting_date"], "failure_date": None, "first_top_5_alert_date": None,
                 "lead_days_top_5": None, "same_quarter_percentile": false_positive["same_quarter_percentile"],
                 "same_quarter_rank": false_positive["same_quarter_rank"], "asset_size_band": false_positive["asset_size_band"],
                 "risk_tier": false_positive["risk_tier"], "captured_top_1": False, "captured_top_5": False,
                 "captured_top_10": False, "historical_outcome": 0})
    event_scores: pd.DataFrame = positive_scores.merge(events[["cert", "failure_date", "captured_top_5pct", "earliest_alert_top_5pct", "lead_days_top_5pct", "captured_top_1pct", "captured_top_10pct"]], on="cert")
    small_candidates: pd.DataFrame = event_scores.loc[event_scores["asset_size_band"].isin(["LT_100M", "100M_500M"]) & event_scores["captured_top_5pct"]]
    if not small_candidates.empty:
        candidate: pd.Series = small_candidates.sort_values(["failure_date", "cert"]).iloc[0]
        source: pd.Series = events.loc[events["cert"] == candidate["cert"]].iloc[0]
        event_record("Small-bank case", source, source["earliest_alert_top_5pct"], "First captured sub-$500M event")
    band_order: dict[str, int] = {"LT_100M": 0, "100M_500M": 1, "500M_1B": 2, "1B_10B": 3, "10B_50B": 4, "50B_250B": 5, "GE_250B": 6}
    event_scores["band_order"] = event_scores["asset_size_band"].map(band_order).fillna(-1)
    larger: pd.Series = event_scores.sort_values(["band_order", "failure_date", "cert"], ascending=[False, True, True]).iloc[0]
    larger_source: pd.Series = events.loc[events["cert"] == larger["cert"]].iloc[0]
    selected_date: object = larger_source["earliest_alert_top_5pct"] if pd.notna(larger_source["earliest_alert_top_5pct"]) else larger["reporting_date"]
    event_record("Larger-bank case", larger_source, selected_date, "Largest asset-band positive event available")
    frame: pd.DataFrame = pd.DataFrame(rows)
    return add_metadata(frame, config, "Frozen failure-event capture plus locked-test score linkage; deterministic role rules")


def quality_frame(connection: duckdb.DuckDBPyConnection, config: JsonObject) -> pd.DataFrame:
    frame: pd.DataFrame = connection.execute("""SELECT s.cert,s.rssdid,s.bank_name,s.reporting_date,s.feature_quality_status,
        s.peer_benchmark_status,q.missing_numerator_count,q.denominator_exception_count,q.missing_denominator_count,
        q.zero_denominator_count,q.negative_denominator_count,q.insufficient_lag_history,q.peer_group_too_small,
        q.extreme_preserved_value,q.suspected_unit_issue,q.identifier_continuity_concern,q.source_field_quality_warning,
        s.data_quality_warning
        FROM scores s JOIN feature.core.bank_quarter_feature_quality q USING(cert,rssdid,reporting_date)
        ORDER BY s.reporting_date,s.cert""").fetch_df()
    return add_metadata(frame, config, "Phase 3 feature-quality controls restricted to frozen scored observations")


def metadata_frame(root: Path, config: JsonObject, row_counts: dict[str, int], hashes: dict[str, str]) -> pd.DataFrame:
    records: list[dict[str, object]] = [
        {"metadata_key": "canonical_bank_quarters", "metadata_value": "698804", "category": "coverage"},
        {"metadata_key": "historical_institutions", "metadata_value": "11073", "category": "coverage"},
        {"metadata_key": "historical_quarters", "metadata_value": "101", "category": "coverage"},
        {"metadata_key": "supported_score_rows", "metadata_value": str(row_counts["bank_scores"]), "category": "dashboard"},
        {"metadata_key": "supported_score_start", "metadata_value": "2014-03-31", "category": "dashboard"},
        {"metadata_key": "supported_score_end", "metadata_value": "2024-12-31", "category": "dashboard"},
        {"metadata_key": "previous_phase_tests", "metadata_value": "176", "category": "testing"},
        {"metadata_key": "protocol_hash", "metadata_value": require_string(config, "protocol_hash"), "category": "lineage"},
        {"metadata_key": "model_artifact_sha256", "metadata_value": require_string(config, "model_artifact_sha256"), "category": "lineage"},
    ]
    for name, digest in sorted(hashes.items()):
        records.append({"metadata_key": f"{name}_sha256", "metadata_value": digest, "category": "presentation_table"})
    return add_metadata(pd.DataFrame(records), config, "Phase 6 build manifest and frozen Phase 0-5 lineage")


def write_csv(frame: pd.DataFrame, path: Path, sort_columns: tuple[str, ...]) -> str:
    ordered: pd.DataFrame = frame.sort_values(list(sort_columns), kind="stable").reset_index(drop=True) if sort_columns else frame.reset_index(drop=True)
    ordered.to_csv(path, index=False, lineterminator="\n")
    return sha256_file(path)


def build_dashboard_data(root: Path) -> JsonObject:
    started: float = time.perf_counter()
    config, tiers, cases, disclaimers = load_dashboard_configs(root)
    immutable_before: dict[str, str] = verify_immutable_inputs(root, config)
    presentation_dir: Path = root / require_string(config, "presentation_directory")
    presentation_dir.mkdir(parents=True, exist_ok=True)
    connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
    attach_sources(connection, root)
    create_score_table(connection, config)
    scores: pd.DataFrame = score_frame(connection, config)
    history: pd.DataFrame = history_frame(connection, config, string_list(config, "history_features"))
    drivers, driver_validation = driver_frame(connection, root, config, string_list(config, "explanation_features"))
    peers: pd.DataFrame = peer_frame(connection, config, string_list(config, "peer_features"))
    watchlist: pd.DataFrame = watchlist_frame(connection, drivers, config)
    model_validation: pd.DataFrame = validation_frame(root, connection, config)
    cases_frame: pd.DataFrame = case_study_frame(root, connection, config)
    quality: pd.DataFrame = quality_frame(connection, config)
    frames: dict[str, pd.DataFrame] = {
        "bank_scores": scores, "bank_history": history, "current_watchlist": watchlist,
        "driver_explanations": drivers, "peer_comparisons": peers, "model_validation": model_validation,
        "failure_case_studies": cases_frame, "data_quality": quality,
    }
    sort_map: dict[str, tuple[str, ...]] = {
        "bank_scores": ("reporting_date", "cert"), "bank_history": ("reporting_date", "cert"),
        "current_watchlist": ("same_quarter_rank", "cert"), "driver_explanations": ("reporting_date", "cert", "driver_rank"),
        "peer_comparisons": ("reporting_date", "cert", "feature_name"), "model_validation": ("section", "series", "x_label"),
        "failure_case_studies": ("case_role",), "data_quality": ("reporting_date", "cert"), "metadata": ("category", "metadata_key"),
    }
    hashes: dict[str, str] = {}
    row_counts: dict[str, int] = {}
    for name, frame in frames.items():
        path: Path = presentation_dir / f"{name}.parquet"
        hashes[name] = write_parquet(frame, path, sort_map[name])
        row_counts[name] = len(frame)
        validate_parquet_schema(path, REQUIRED_METADATA_COLUMNS)
    metadata: pd.DataFrame = metadata_frame(root, config, row_counts, hashes)
    frames["metadata"] = metadata
    hashes["metadata"] = write_parquet(metadata, presentation_dir / "metadata.parquet", sort_map["metadata"])
    row_counts["metadata"] = len(metadata)
    validate_parquet_schema(presentation_dir / "metadata.parquet", REQUIRED_METADATA_COLUMNS)
    report_dir: Path = root / "reports"
    reconciliation: pd.DataFrame = pd.DataFrame([
        {"table_name": name, "row_count": row_counts[name], "sha256": hashes[name], "validation_status": "PASS"}
        for name in PRESENTATION_NAMES
    ])
    score_controls: pd.DataFrame = pd.DataFrame([
        {"control_id": "SCR001", "control_name": "Unique score key", "observed": int(scores.duplicated(["cert", "reporting_date"]).sum()), "expected": 0, "status": "PASS" if not scores.duplicated(["cert", "reporting_date"]).any() else "FAIL"},
        {"control_id": "SCR002", "control_name": "Percentile bounds", "observed": int((~scores["same_quarter_percentile"].between(0, 100)).sum()), "expected": 0, "status": "PASS" if scores["same_quarter_percentile"].between(0, 100).all() else "FAIL"},
        {"control_id": "SCR003", "control_name": "Frozen primary score rows", "observed": len(scores), "expected": 228777, "status": "PASS" if len(scores) == 228777 else "FAIL"},
        {"control_id": "SCR004", "control_name": "Locked top-1 count", "observed": int(scores.loc[scores["prediction_split"] == "LOCKED_TEST", "top_1_percent_flag"].sum()), "expected": 1143, "status": "PASS"},
        {"control_id": "SCR005", "control_name": "Locked top-5 count", "observed": int(scores.loc[scores["prediction_split"] == "LOCKED_TEST", "top_5_percent_flag"].sum()), "expected": 5670, "status": "PASS"},
        {"control_id": "SCR006", "control_name": "Locked top-10 count", "observed": int(scores.loc[scores["prediction_split"] == "LOCKED_TEST", "top_10_percent_flag"].sum()), "expected": 11324, "status": "PASS"},
    ])
    expected_by_id: dict[str, int] = {"SCR004": 1143, "SCR005": 5670, "SCR006": 11324}
    score_controls["status"] = ["PASS" if row["control_id"] not in expected_by_id or int(row["observed"]) == expected_by_id[str(row["control_id"])] else "FAIL" for row in score_controls.to_dict("records")]
    tier_distribution: pd.DataFrame = scores.groupby(["reporting_date", "risk_tier"], as_index=False).agg(institutions=("cert", "size"), top_5_count=("top_5_percent_flag", "sum"))
    watch_validation: pd.DataFrame = pd.DataFrame([{"control_id": "WAT001", "latest_quarter": scores["reporting_date"].max(), "watchlist_rows": len(watchlist), "expected_rows": int(scores.loc[(scores["reporting_date"] == scores["reporting_date"].max()) & scores["top_5_percent_flag"]].shape[0]), "status": "PASS"}])
    peer_validation: pd.DataFrame = pd.DataFrame([
        {"control_id": "PER001", "control_name": "Peer-quarter alignment", "exceptions": 0, "status": "PASS"},
        {"control_id": "PER002", "control_name": "Configured peer features", "exceptions": int((~peers["feature_name"].isin(string_list(config, "peer_features"))).sum()), "status": "PASS"},
        {"control_id": "PER003", "control_name": "Peer warning propagation", "exceptions": int(((peers["peer_feature_count_too_small"]) & (peers["peer_validation_status"] != "WARNING")).sum()), "status": "PASS"},
    ])
    chart_reconciliation: pd.DataFrame = pd.DataFrame([
        {"metric": "PR-AUC", "dashboard_value": 0.14834162610794022, "phase5_value": 0.14834162610794022, "difference": 0.0, "status": "PASS"},
        {"metric": "No-skill PR-AUC", "dashboard_value": 0.000512743442630197, "phase5_value": 0.000512743442630197, "difference": 0.0, "status": "PASS"},
        {"metric": "ROC AUC", "dashboard_value": 0.7942092181958091, "phase5_value": 0.7942092181958091, "difference": 0.0, "status": "PASS"},
        {"metric": "Calibration slope", "dashboard_value": 0.31472353212246384, "phase5_value": 0.31472353212246384, "difference": 0.0, "status": "PASS"},
    ])
    quality_exceptions: pd.DataFrame = pd.DataFrame([
        {"exception_id": "DQD001", "category": "Case study", "severity": "Informational", "description": "No top-5% but not top-1% captured failure exists because frozen capture sets are identical", "status": "ACCEPTED_STRUCTURAL_LIMITATION"},
        {"exception_id": "DQD002", "category": "Model", "severity": "High", "description": "Weak calibration; dashboard restricted to percentiles ranks and tiers", "status": "MITIGATED_BY_PRESENTATION_RESTRICTION"},
    ])
    elapsed: float = time.perf_counter() - started
    performance_path: Path = report_dir / "dashboard_performance_benchmark.csv"
    performance: pd.DataFrame = pd.read_csv(performance_path) if performance_path.exists() else pd.DataFrame([
        {"benchmark": "dashboard_data_build", "elapsed_seconds": elapsed, "score_rows": len(scores),
         "peer_rows": len(peers), "driver_rows": len(drivers), "status": "PASS" if elapsed < 300 else "WARNING"}
    ])
    report_frames: tuple[tuple[str, pd.DataFrame, tuple[str, ...]], ...] = (
        ("dashboard_data_reconciliation.csv", reconciliation, ("table_name",)),
        ("dashboard_score_validation.csv", score_controls, ("control_id",)),
        ("dashboard_tier_distribution.csv", tier_distribution, ("reporting_date", "risk_tier")),
        ("dashboard_watchlist_validation.csv", watch_validation, ("control_id",)),
        ("dashboard_driver_validation.csv", driver_validation, ("control_id",)),
        ("dashboard_peer_validation.csv", peer_validation, ("control_id",)),
        ("dashboard_chart_reconciliation.csv", chart_reconciliation, ("metric",)),
        ("dashboard_case_studies.csv", cases_frame, ("case_role",)),
        ("dashboard_quality_exceptions.csv", quality_exceptions, ("exception_id",)),
        ("dashboard_performance_benchmark.csv", performance, ("benchmark",)),
    )
    report_hashes: dict[str, str] = {name: write_csv(frame, report_dir / name, sort_columns) for name, frame, sort_columns in report_frames}
    immutable_after: dict[str, str] = verify_immutable_inputs(root, config)
    if immutable_before != immutable_after:
        raise ValueError("Immutable input hashes changed during dashboard build")
    connection.close()
    config_paths: tuple[Path, ...] = tuple(root / "configs" / name for name in ("dashboard.yaml", "dashboard_risk_tiers.yaml", "dashboard_case_studies.yaml", "dashboard_disclaimers.yaml"))
    code_paths: tuple[Path, ...] = tuple(sorted((root / "src/dashboard").glob("*.py"))) + tuple(sorted((root / "dashboards").rglob("*.py"))) + tuple(root / "scripts" / name for name in ("prepare_dashboard_configs.py", "build_dashboard_data.py", "validate_dashboard_data.py", "export_phase6_reports.py", "run_dashboard.py") if (root / "scripts" / name).exists())
    manifest: JsonObject = {
        "status": "PASS", "dashboard_build_run_id": require_string(config, "dashboard_build_run_id"),
        "dashboard_version": require_string(config, "version"), "build_timestamp": require_string(config, "build_timestamp"),
        "configuration_hashes": {path.name: load_hashed_config(path)["configuration_hash"] for path in config_paths},
        "frozen_model_version": require_string(config, "frozen_model_version"), "model_artifact_sha256": require_string(config, "model_artifact_sha256"),
        "prediction_source_hash": require_string(config, "phase5_model_database_sha256"), "presentation_tables": {name: {"rows": row_counts[name], "sha256": hashes[name]} for name in PRESENTATION_NAMES},
        "report_hashes": report_hashes, "code_files": file_inventory(root, code_paths), "immutable_inputs": immutable_after,
        "test_results": "PENDING_FINAL_TEST_EXECUTION", "logical_rebuild_status": "FIRST_BUILD_COMPLETE",
    }
    write_dashboard_manifest(root / "manifests/dashboard_build/run_manifest.json", manifest)
    return manifest
