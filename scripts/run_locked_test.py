"""Perform the single governed Phase 5 locked-test access and evaluation."""

from __future__ import annotations

import json
import pickle
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, sha256_file  # noqa: E402
from src.models.calibration import apply_calibrator  # noqa: E402
from src.models.config import included_features, load_hashed_config, require_string  # noqa: E402
from src.models.evaluator import evaluate_predictions, reliability_table  # noqa: E402
from src.models.event_metrics import failure_event_capture  # noqa: E402
from src.models.registry import replace_table_from_frame  # noqa: E402
from src.models.thresholds import quarter_budget_flags  # noqa: E402
from src.models.trainer import FittedCandidate, predict_candidate  # noqa: E402
from src.models.uncertainty import confidence_intervals, event_bootstrap, institution_cluster_bootstrap  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_access_log(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["access_id", "started_at", "completed_at", "command", "status", "protocol_hash", "pre_test_commit", "notes"])
    return pd.read_csv(path, dtype=str).fillna("")


def write_access_log(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def require_pre_test_gate(manifest: JsonObject, access_log: pd.DataFrame) -> str:
    if manifest.get("status") != "FROZEN_BEFORE_LOCKED_TEST" or manifest.get("locked_test_accessed") is not False:
        raise RuntimeError("Pre-test manifest is not in the frozen, unaccessed state")
    completed: int = int((access_log["status"] == "COMPLETED").sum()) if not access_log.empty else 0
    if completed >= 1:
        raise RuntimeError("Locked-test policy violation prevented: a completed access already exists")
    tags: str = subprocess.run(["git", "tag", "--list", "phase5-pre-test-model-frozen"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    if tags != "phase5-pre-test-model-frozen":
        raise RuntimeError("Required pre-test tag phase5-pre-test-model-frozen is missing")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def load_artifact(path: Path, expected_hash: str) -> object:
    observed: str = sha256_file(path)
    if observed != expected_hash:
        raise ValueError(f"Frozen artifact hash mismatch: path={path}, expected={expected_hash}, observed={observed}")
    with path.open("rb") as handle:
        return pickle.load(handle)


def locked_frame(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    label_table: str,
    outcome_column: str,
    status_column: str,
    feature_names: tuple[str, ...],
) -> pd.DataFrame:
    feature_sql: str = ",".join(f'd."{name}"' for name in feature_names)
    next_failure: str = "l.next_failure_date" if label_table.endswith("failure_labels") else "CAST(NULL AS DATE)"
    query: str = f"""SELECT d.cert,d.rssdid,d.reporting_date,d.asset_size_band,d.bank_class,d.feature_quality_status,
        {feature_sql},CAST(l.{outcome_column} AS INTEGER) AS target,{next_failure} AS next_failure_date
        FROM core.{table_name} d
        JOIN {label_table} l USING(cert,rssdid,reporting_date)
        WHERE d.split_assignment='LOCKED_TEST' AND l.{status_column} IN ('POSITIVE','NEGATIVE')
        ORDER BY d.reporting_date,d.cert"""
    frame: pd.DataFrame = connection.execute(query).fetch_df()
    if frame.empty or frame["target"].isna().any():
        raise ValueError(f"Locked-test extraction failed for {table_name}: rows={len(frame)}")
    if frame.duplicated(["cert", "reporting_date"]).any():
        raise ValueError(f"Duplicate locked-test keys for {table_name}")
    return frame


def subgroup_metrics(predictions: pd.DataFrame, group_column: str, threshold: float, budgets: tuple[float, ...]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for value, group in predictions.groupby(group_column, dropna=False):
        positives: int = int(group["target"].sum())
        if positives == 0 or int((1 - group["target"]).sum()) == 0:
            rows.append({"group": value, "observations": len(group), "positives": positives, "reliability": "INSUFFICIENT_EVENTS"})
            continue
        result: dict[str, Any] = evaluate_predictions(
            group[["cert", "rssdid", "reporting_date"]], group["target"].to_numpy(dtype=int),
            group["probability"].to_numpy(dtype=float), threshold, budgets,
        )
        rows.append({"group": value, **result, "reliability": "REPORT_WITH_CAUTION" if positives < 10 else "ASSESSABLE"})
    return pd.DataFrame(rows)


def threshold_report(predictions: pd.DataFrame, outcome_name: str, threshold: float, budgets: tuple[float, ...]) -> pd.DataFrame:
    y: np.ndarray = predictions["target"].to_numpy(dtype=int)
    rows: list[dict[str, Any]] = []
    for budget in budgets:
        flags: np.ndarray = quarter_budget_flags(predictions[["cert", "reporting_date"]], predictions["probability"].to_numpy(dtype=float), budget)
        captured: int = int(y[flags].sum())
        rows.append({"outcome_name": outcome_name, "threshold_type": "SAME_QUARTER_BUDGET", "alert_budget": budget,
                     "threshold_value": None, "alerts": int(flags.sum()), "false_alerts": int(flags.sum()) - captured,
                     "precision": captured / int(flags.sum()), "recall": captured / int(y.sum())})
    fixed: np.ndarray = predictions["probability"].to_numpy(dtype=float) >= threshold
    captured_fixed: int = int(y[fixed].sum())
    rows.append({"outcome_name": outcome_name, "threshold_type": "FROZEN_F2_PROBABILITY", "alert_budget": None,
                 "threshold_value": threshold, "alerts": int(fixed.sum()), "false_alerts": int(fixed.sum()) - captured_fixed,
                 "precision": captured_fixed / int(fixed.sum()) if fixed.any() else 0.0,
                 "recall": captured_fixed / int(y.sum())})
    return pd.DataFrame(rows)


def main() -> None:
    manifest_path: Path = ROOT / "manifests/model_experiment/pre_test_selection_manifest.json"
    manifest: JsonObject = json.loads(manifest_path.read_text(encoding="utf-8"))
    access_path: Path = ROOT / "reports/locked_test_access_log.csv"
    access_log: pd.DataFrame = read_access_log(access_path)
    pre_test_commit: str = require_pre_test_gate(manifest, access_log)
    access_id: str = "phase5-locked-test-001"
    access_row: dict[str, str] = {"access_id": access_id, "started_at": utc_now(), "completed_at": "",
                                  "command": "python scripts/run_locked_test.py", "status": "STARTED",
                                  "protocol_hash": str(manifest["protocol_hash"]), "pre_test_commit": pre_test_commit,
                                  "notes": "Single primary and secondary outcome access"}
    access_log = pd.concat([access_log, pd.DataFrame([access_row])], ignore_index=True)
    write_access_log(access_path, access_log)
    try:
        feature_config: JsonObject = load_hashed_config(ROOT / "configs/model_features.yaml")
        metrics_config: JsonObject = load_hashed_config(ROOT / "configs/evaluation_metrics.yaml")
        feature_names: tuple[str, ...] = included_features(feature_config)
        budgets: tuple[float, ...] = tuple(float(value) for value in metrics_config["alert_budgets"])  # type: ignore[index]
        database_path: Path = ROOT / "database/bank_risk_models.duckdb"
        phase4_path: str = str(ROOT / "database/bank_risk_labels.duckdb").replace("\\", "/").replace("'", "''")
        connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path), read_only=True)
        connection.execute(f"ATTACH '{phase4_path}' AS phase4 (READ_ONLY)")
        specifications: tuple[tuple[str, str, str, str, str], ...] = (
            ("failure_4q", "model_dataset_failure_4q", "phase4.core.bank_quarter_failure_labels", "failed_within_4_quarters", "failure_label_status_4q"),
            ("failure_8q", "model_dataset_failure_8q", "phase4.core.bank_quarter_failure_labels", "failed_within_8_quarters", "failure_label_status_8q"),
            ("deterioration_4q", "model_dataset_deterioration_4q", "phase4.core.bank_quarter_distress_labels", "severe_deterioration_within_4_quarters", "distress_label_status"),
        )
        metric_rows: list[dict[str, Any]] = []
        prediction_rows: list[pd.DataFrame] = []
        threshold_rows: list[pd.DataFrame] = []
        calibration_rows: list[pd.DataFrame] = []
        uncertainty_rows: list[pd.DataFrame] = []
        primary_predictions: pd.DataFrame | None = None
        primary_threshold: float = 0.0
        for outcome_name, table_name, label_table, outcome_column, status_column in specifications:
            selection: JsonObject = manifest["outcome_selections"][outcome_name]  # type: ignore[index,assignment]
            model_path: Path = ROOT / require_string(selection, "model_path")
            calibrator_path: Path = ROOT / require_string(selection, "calibrator_path")
            model: FittedCandidate = load_artifact(model_path, require_string(selection, "model_sha256"))  # type: ignore[assignment]
            calibrator: dict[str, Any] = load_artifact(calibrator_path, require_string(selection, "calibrator_sha256"))  # type: ignore[assignment]
            frame: pd.DataFrame = locked_frame(connection, table_name, label_table, outcome_column, status_column, feature_names)
            raw_probability: np.ndarray = predict_candidate(model, frame.loc[:, feature_names].astype(float).replace([np.inf, -np.inf], np.nan))
            probability: np.ndarray = apply_calibrator(calibrator, raw_probability)
            threshold: float = float(selection["classification_threshold"])
            result: dict[str, Any] = evaluate_predictions(frame[["cert", "rssdid", "reporting_date"]], frame["target"].to_numpy(dtype=int), probability, threshold, budgets)
            metric_rows.append({"outcome_name": outcome_name, "model_id": selection["model_id"], "split": "LOCKED_TEST", **result,
                                "pr_auc_lift": result["average_precision"] / result["baseline_average_precision"]})
            output: pd.DataFrame = frame[["cert", "rssdid", "reporting_date", "target", "next_failure_date", "asset_size_band", "bank_class", "feature_quality_status"]].copy()
            output["outcome_name"] = outcome_name
            output["model_id"] = selection["model_id"]
            output["raw_probability"] = raw_probability
            output["probability"] = probability
            output["protocol_hash"] = manifest["protocol_hash"]
            prediction_rows.append(output)
            threshold_rows.append(threshold_report(output, outcome_name, threshold, budgets))
            reliability: pd.DataFrame = reliability_table(output["target"].to_numpy(dtype=int), probability, 10)
            reliability.insert(0, "outcome_name", outcome_name)
            reliability.insert(1, "calibration_method", selection["calibration_method"])
            calibration_rows.append(reliability)
            draws: pd.DataFrame = institution_cluster_bootstrap(output[["cert", "target", "probability"]], 200, 20260718)
            intervals: pd.DataFrame = confidence_intervals(draws)
            intervals.insert(0, "outcome_name", outcome_name)
            intervals["bootstrap_unit"] = "institution"
            uncertainty_rows.append(intervals)
            if outcome_name == "failure_4q":
                primary_predictions = output
                primary_threshold = threshold
        connection.close()
        if primary_predictions is None:
            raise RuntimeError("Primary locked-test predictions were not produced")
        predictions: pd.DataFrame = pd.concat(prediction_rows, ignore_index=True)
        metrics: pd.DataFrame = pd.DataFrame(metric_rows)
        thresholds: pd.DataFrame = pd.concat(threshold_rows, ignore_index=True)
        calibration: pd.DataFrame = pd.concat(calibration_rows, ignore_index=True)
        uncertainty: pd.DataFrame = pd.concat(uncertainty_rows, ignore_index=True)
        events: pd.DataFrame = failure_event_capture(primary_predictions, budgets)
        event_draws: pd.DataFrame = event_bootstrap(events, 200, 20260718, budgets)
        for budget in budgets:
            column: str = f"capture_top_{int(budget*100)}pct"
            uncertainty = pd.concat([uncertainty, pd.DataFrame([{
                "outcome_name": "failure_4q", "metric": column,
                "lower_95": event_draws[column].quantile(0.025), "median": event_draws[column].median(),
                "upper_95": event_draws[column].quantile(0.975), "bootstrap_unit": "unique_failure_event",
            }])], ignore_index=True)
        reports: Path = ROOT / "reports"
        metrics.to_csv(reports / "locked_test_metrics.csv", index=False, lineterminator="\n")
        thresholds.to_csv(reports / "locked_test_threshold_results.csv", index=False, lineterminator="\n")
        calibration.to_csv(reports / "locked_test_calibration.csv", index=False, lineterminator="\n")
        events.to_csv(reports / "failure_event_capture.csv", index=False, lineterminator="\n")
        events.to_csv(reports / "failure_lead_time_by_event.csv", index=False, lineterminator="\n")
        metrics.loc[metrics["outcome_name"] != "failure_4q"].to_csv(reports / "secondary_outcome_results.csv", index=False, lineterminator="\n")
        uncertainty.to_csv(reports / "model_uncertainty_intervals.csv", index=False, lineterminator="\n")
        primary_predictions = primary_predictions.assign(reporting_year=pd.to_datetime(primary_predictions["reporting_date"]).dt.year,
                                                         reporting_quarter=pd.to_datetime(primary_predictions["reporting_date"]).dt.to_period("Q").astype(str))
        subgroup_metrics(primary_predictions, "reporting_year", primary_threshold, budgets).rename(columns={"group": "reporting_year"}).to_csv(reports / "model_performance_by_period.csv", index=False, lineterminator="\n")
        subgroup_metrics(primary_predictions, "reporting_quarter", primary_threshold, budgets).rename(columns={"group": "reporting_quarter"}).to_csv(reports / "model_performance_by_quarter.csv", index=False, lineterminator="\n")
        subgroup_metrics(primary_predictions, "asset_size_band", primary_threshold, budgets).rename(columns={"group": "asset_size_band"}).to_csv(reports / "model_performance_by_asset_band.csv", index=False, lineterminator="\n")
        subgroup_metrics(primary_predictions, "bank_class", primary_threshold, budgets).rename(columns={"group": "bank_class"}).to_csv(reports / "model_performance_by_bank_class.csv", index=False, lineterminator="\n")
        subgroup_metrics(primary_predictions, "feature_quality_status", primary_threshold, budgets).rename(columns={"group": "feature_quality_status"}).to_csv(reports / "model_performance_by_feature_quality.csv", index=False, lineterminator="\n")
        registry_predictions: pd.DataFrame = predictions[["cert", "rssdid", "reporting_date", "outcome_name", "model_id", "target", "raw_probability", "probability", "asset_size_band", "bank_class", "feature_quality_status", "protocol_hash"]]
        replace_table_from_frame(ROOT / "database/bank_risk_models.duckdb", "modeling.locked_test_predictions", registry_predictions)
        long_metrics: pd.DataFrame = metrics.melt(id_vars=["outcome_name", "model_id", "split"], var_name="metric_name", value_name="metric_value")
        long_metrics["protocol_hash"] = manifest["protocol_hash"]
        replace_table_from_frame(ROOT / "database/bank_risk_models.duckdb", "modeling.model_metrics", long_metrics)
        access_log.loc[access_log["access_id"] == access_id, ["completed_at", "status"]] = [utc_now(), "COMPLETED"]
        write_access_log(access_path, access_log)
        print(f"PASS locked_test_access=1 primary_ap={metrics.iloc[0]['average_precision']:.6f} events={len(events)}")
    except Exception as error:
        access_log.loc[access_log["access_id"] == access_id, ["completed_at", "status", "notes"]] = [utc_now(), "FAILED", str(error)]
        write_access_log(access_path, access_log)
        raise


if __name__ == "__main__":
    main()
