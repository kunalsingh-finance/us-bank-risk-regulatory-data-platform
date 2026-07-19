"""Populate the Phase 5 DuckDB registries from frozen reports and manifests."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]


def replace(connection: duckdb.DuckDBPyConnection, table: str, frame: pd.DataFrame) -> None:
    connection.register("report_frame", frame)
    connection.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM report_frame")
    connection.unregister("report_frame")


def main() -> None:
    selection = json.loads((ROOT / "manifests/model_experiment/pre_test_selection_manifest.json").read_text(encoding="utf-8"))
    protocol_hash: str = str(selection["protocol_hash"])
    registry_rows: list[dict[str, object]] = []
    for outcome, raw in selection["outcome_selections"].items():
        registry_rows.append({"model_id": raw["model_id"], "outcome_name": outcome, "family": raw["family"],
                              "parameters_json": json.dumps(raw["parameters"], sort_keys=True),
                              "artifact_path": raw["model_path"], "artifact_sha256": raw["model_sha256"],
                              "selected": True, "protocol_hash": protocol_hash})
    candidates: pd.DataFrame = pd.read_csv(ROOT / "reports/candidate_model_results.csv")
    training_runs: pd.DataFrame = candidates[["model_id", "fold", "train_start", "train_end", "validation_start", "validation_end"]].copy()
    training_runs.insert(0, "run_id", [f"phase5-cv-{index + 1:03d}" for index in range(len(training_runs))])
    training_runs["outcome_name"] = "failure_4q"
    training_runs["status"] = "COMPLETED"
    metrics: pd.DataFrame = pd.read_csv(ROOT / "reports/locked_test_metrics.csv")
    long_metrics: pd.DataFrame = metrics.melt(id_vars=["outcome_name", "model_id", "split"], var_name="metric_name", value_name="metric_value")
    long_metrics["protocol_hash"] = protocol_hash
    calibration: pd.DataFrame = pd.read_csv(ROOT / "reports/validation_calibration.csv")
    calibration["outcome_name"] = "failure_4q"
    calibration["model_id"] = selection["selected_model"]
    calibration["evaluation_period"] = "VALIDATION_SELECTION"
    calibration = calibration.rename(columns={"expected_calibration_error": "ece"})
    importance: pd.DataFrame = pd.read_csv(ROOT / "reports/model_feature_importance.csv").rename(
        columns={"importance_mean": "importance_value"}
    )
    importance["outcome_name"] = "failure_4q"
    if "importance_std" not in importance:
        importance["importance_std"] = None
    events: pd.DataFrame = pd.read_csv(ROOT / "reports/failure_event_capture.csv")
    thresholds: pd.DataFrame = pd.read_csv(ROOT / "reports/locked_test_threshold_results.csv")
    thresholds["model_id"] = selection["selected_model"]
    thresholds["split"] = "LOCKED_TEST"
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(ROOT / "database/bank_risk_models.duckdb"))
    diagnostics: pd.DataFrame = connection.execute("""SELECT dataset_name,split_assignment,COUNT(*) observations,
        COUNT(outcome) labelled_observations,SUM(COALESCE(outcome,0)) positives,COUNT(DISTINCT cert) institutions,
        MIN(reporting_date) first_date,MAX(reporting_date) last_date
        FROM (SELECT 'failure_4q' AS dataset_name,* FROM core.model_dataset_failure_4q
              UNION ALL BY NAME SELECT 'failure_8q' AS dataset_name,* FROM core.model_dataset_failure_8q
              UNION ALL BY NAME SELECT 'deterioration_4q' AS dataset_name,* FROM core.model_dataset_deterioration_4q)
        GROUP BY dataset_name,split_assignment ORDER BY dataset_name,split_assignment""").fetch_df()
    diagnostics.to_csv(ROOT / "reports/split_diagnostics.csv", index=False, lineterminator="\n")
    replace(connection, "modeling.model_registry", pd.DataFrame(registry_rows))
    replace(connection, "modeling.training_runs", training_runs)
    replace(connection, "modeling.model_metrics", long_metrics)
    replace(connection, "modeling.calibration_results", calibration[["outcome_name", "model_id", "method", "evaluation_period", "brier_score", "calibration_intercept", "calibration_slope", "ece", "selected"]])
    replace(connection, "modeling.failure_event_capture", events)
    replace(connection, "modeling.feature_importance", importance)
    replace(connection, "modeling.threshold_results", thresholds)
    counts = connection.execute("""SELECT
        (SELECT COUNT(*) FROM modeling.model_registry),
        (SELECT COUNT(*) FROM modeling.training_runs),
        (SELECT COUNT(*) FROM modeling.locked_test_predictions),
        (SELECT COUNT(*) FROM modeling.failure_event_capture)""").fetchone()
    connection.close()
    print(f"PASS registry={counts[0]} training_runs={counts[1]} predictions={counts[2]} events={counts[3]}")


if __name__ == "__main__":
    main()
