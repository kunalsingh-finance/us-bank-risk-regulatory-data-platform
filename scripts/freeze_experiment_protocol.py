"""Freeze the governed Phase 5 protocol before any final model fitting."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import (  # noqa: E402
    JsonObject,
    configuration_hash,
    load_json_object,
    sha256_file,
    write_replaceable_json,
)


EXCLUDED_FEATURES: dict[str, str] = {
    "capital_deterioration_flag": "Screening flag; descriptive only",
    "asset_quality_deterioration_flag": "Screening flag; descriptive only",
    "earnings_deterioration_flag": "Screening flag; descriptive only",
    "liquidity_deterioration_flag": "Screening flag; descriptive only",
    "funding_pressure_flag": "Screening flag; descriptive only",
    "concentration_pressure_flag": "Screening flag; descriptive only",
    "rapid_asset_growth_flag": "Screening flag; descriptive only",
    "rapid_loan_growth_flag": "Screening flag; descriptive only",
    "funding_gap_flag": "Screening flag; descriptive only",
    "assessable_deposits_to_total_deposits": "Descriptive assessment-base share",
    "reported_real_estate_loans_to_total_loans": "Incomplete business-mix descriptor",
    "construction_to_total_loans": "Non-monotonic business-mix share",
    "multifamily_to_total_loans": "Non-monotonic business-mix share",
    "residential_mortgages_to_total_loans": "Non-monotonic business-mix share",
    "commercial_industrial_to_total_loans": "Non-monotonic business-mix share",
    "consumer_to_total_loans": "Non-monotonic business-mix share",
    "credit_card_to_total_loans": "Non-monotonic business-mix share",
    "loan_category_coverage_ratio": "Coverage diagnostic, not a risk predictor",
}


def freeze(payload: JsonObject, path: Path) -> JsonObject:
    frozen: JsonObject = dict(payload)
    frozen["configuration_hash"] = configuration_hash(frozen)
    write_replaceable_json(path, frozen)
    return frozen


def inventory_by_name(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {str(row["feature_name"]): dict(row) for row in csv.DictReader(handle)}


def main() -> None:
    risk: JsonObject = load_json_object(ROOT / "configs/risk_features.yaml")
    raw_features: object = risk.get("features")
    if not isinstance(raw_features, list):
        raise TypeError("risk_features.yaml features must be a list")
    inventory: dict[str, dict[str, str]] = inventory_by_name(ROOT / "reports/feature_inventory.csv")
    feature_records: list[JsonObject] = []
    included_names: list[str] = []
    for raw in raw_features:
        if not isinstance(raw, dict):
            raise TypeError(f"Invalid feature entry: {raw!r}")
        name: str = str(raw["feature_name"])
        included: bool = name not in EXCLUDED_FEATURES
        if included:
            included_names.append(name)
        feature_records.append({
            "feature_name": name,
            "included": included,
            "category": raw["financial_category"],
            "source_table": "phase3.core.bank_quarter_risk_features",
            "risk_direction": raw["direction_of_risk"],
            "availability_period": raw["availability_period"],
            "missingness_rate": float(inventory[name]["missing_percentage"]),
            "conditional_field_status": "Not conditional",
            "peer_group_eligibility_requirement": "None; peer statistics excluded from v1 predictors",
            "transformation": "Raw value retained; training-fold median imputation only",
            "scaling_requirement": "Training-fold standardization for linear models",
            "missing_indicator_requirement": True,
            "permitted_model_families": ["rule_score", "logistic", "regularized_logistic", "random_forest", "hist_gradient_boosting"] if included else [],
            "exclusion_rationale": EXCLUDED_FEATURES.get(name, ""),
        })
    features: JsonObject = freeze({
        "version": "phase5-model-features-v2",
        "identifier_columns": ["cert", "rssdid", "reporting_date"],
        "audit_only_columns": ["asset_size_band", "bank_class", "feature_quality_status"],
        "prohibited_predictor_patterns": ["failure", "closing", "acquiring", "fund_number", "event", "label", "censor", "future", "source", "hash", "cert", "rssdid", "name"],
        "included_feature_count": len(included_names),
        "included_feature_names": included_names,
        "features": feature_records,
    }, ROOT / "configs/model_features.yaml")
    candidates: JsonObject = freeze({
        "version": "phase5-candidates-v3",
        "random_seed": 20260718,
        "families": {
            "prevalence_baseline": {"grid": [{}]},
            "rule_score": {"grid": [{"features": ["equity_to_assets", "noncurrent_assets_to_total_loans", "return_on_assets", "loans_to_deposits", "funding_cost", "total_asset_growth_yoy_pct"]}]},
            "logistic": {"grid": [{"penalty": "l2", "C": 1000000.0, "solver": "lbfgs"}], "class_weight": "balanced", "max_iter": 1500},
            "regularized_logistic": {"grid": [
                {"optimizer": "sgd", "penalty": "l1", "alpha": 0.0001, "l1_ratio": 1.0},
                {"optimizer": "sgd", "penalty": "l2", "alpha": 0.0001, "l1_ratio": 0.0},
                {"optimizer": "sgd", "penalty": "elasticnet", "alpha": 0.0001, "l1_ratio": 0.5}
            ], "class_weight": "balanced", "max_iter": 250},
            "random_forest": {"grid": [
                {"n_estimators": 100, "max_depth": 8, "min_samples_leaf": 50, "max_features": "sqrt"},
                {"n_estimators": 100, "max_depth": 12, "min_samples_leaf": 50, "max_features": "sqrt"}
            ], "class_weight": "balanced_subsample"},
            "hist_gradient_boosting": {"grid": [
                {"learning_rate": 0.05, "max_iter": 150, "max_leaf_nodes": 15, "min_samples_leaf": 50, "l2_regularization": 1.0},
                {"learning_rate": 0.05, "max_iter": 150, "max_leaf_nodes": 31, "min_samples_leaf": 50, "l2_regularization": 5.0}
            ], "class_weight": "balanced"},
        },
        "smote": {"enabled": False, "reason": "Not part of primary preregistered analysis"},
    }, ROOT / "configs/model_candidates.yaml")
    metrics: JsonObject = freeze({
        "version": "phase5-metrics-v2",
        "primary_model_selection_metric": "average_precision",
        "no_skill_baseline": "positive prevalence",
        "tie_breakers": ["brier_score", "expected_calibration_error", "recall_at_top_5pct", "unique_failure_capture_at_top_5pct", "simplicity"],
        "secondary_metrics": ["roc_auc", "log_loss", "brier_score", "calibration_intercept", "calibration_slope", "expected_calibration_error", "precision", "recall", "f1", "f2", "specificity", "balanced_accuracy", "matthews_correlation_coefficient", "accuracy_with_warning"],
        "alert_budgets": [0.01, 0.05, 0.10],
        "primary_alert_budget": 0.05,
        "subgroup_minimum_positive_events": 10,
        "uncertainty": {"method": "institution-cluster bootstrap", "repetitions": 200, "confidence_level": 0.95, "seed": 20260718},
    }, ROOT / "configs/evaluation_metrics.yaml")
    locked: JsonObject = freeze({
        "version": "phase5-locked-test-v2",
        "test_start": "2019-03-31",
        "test_end": "2024-12-31",
        "maximum_completed_accesses": 1,
        "required_manifest": "manifests/model_experiment/pre_test_selection_manifest.json",
        "required_tag": "phase5-pre-test-model-frozen",
        "access_log": "reports/locked_test_access_log.csv",
        "forbidden_post_access_changes": ["feature contract", "split boundaries", "model family", "hyperparameters", "calibration method", "alert budgets", "thresholds"],
        "implementation_defect_policy": "Invalidate the run, document the defect, remove the pre-test tag only with explicit approval, and complete a new freeze before re-access",
    }, ROOT / "configs/locked_test_policy.yaml")
    protocol: JsonObject = freeze({
        "version": "phase5-experimental-protocol-v3",
        "freeze_timestamp": "2026-07-18T12:00:00Z",
        "preliminary_run_status": "INVALIDATED_BEFORE_LOCKED_TEST",
        "preliminary_run_reason": "The incomplete v1 run omitted required controls; the first v2 development run timed out on non-convergent SAGA fits. Neither run accessed the locked test. V3 uses deterministic averaged SGD for regularized logistic candidates.",
        "outcomes": {
            "primary": {"name": "failed_within_4_quarters", "status_column": "failure_label_status_4q"},
            "secondary": {"name": "failed_within_8_quarters", "status_column": "failure_label_status_8q"},
            "sensitivity": {"name": "severe_deterioration_within_4_quarters", "status_column": "distress_label_status"},
        },
        "eligible_statuses": ["POSITIVE", "NEGATIVE"],
        "excluded_statuses": ["RIGHT_CENSORED", "CENSORED_NONFAILURE_EXIT", "INELIGIBLE_POST_EVENT", "INELIGIBLE_DATA_QUALITY", "INELIGIBLE_INSUFFICIENT_HISTORY", "UNRESOLVED_EVENT_MAPPING"],
        "splits": {
            "train": ["2001-03-31", "2013-12-31"],
            "validation": ["2014-03-31", "2018-12-31"],
            "calibration_fit": ["2014-03-31", "2016-12-31"],
            "validation_selection": ["2017-03-31", "2018-12-31"],
            "locked_test": ["2019-03-31", "2024-12-31"],
        },
        "cross_validation": {"design": "expanding_window", "folds": [
            {"fold": 1, "train": ["2001-03-31", "2006-12-31"], "validation": ["2007-03-31", "2008-12-31"]},
            {"fold": 2, "train": ["2001-03-31", "2008-12-31"], "validation": ["2009-03-31", "2010-12-31"]},
            {"fold": 3, "train": ["2001-03-31", "2010-12-31"], "validation": ["2011-03-31", "2013-12-31"]}
        ]},
        "preprocessing": {"numeric_imputation": "training-fold median", "missing_indicators": True, "linear_scaling": "training-fold StandardScaler", "tree_scaling": "none", "categorical_predictors": [], "clipping": "none"},
        "class_imbalance": {"primary": "class weights and alert-budget ranking", "smote": "not used", "accuracy": "reported with explicit warning only"},
        "calibration": {"candidates": ["none", "platt", "isotonic"], "fit_period": "calibration_fit", "selection_period": "validation_selection", "selection_metric": "brier_score", "isotonic_minimum_positives": 20},
        "threshold_selection": {"classification_threshold": "validation-selection F2", "operational_alert_budget": "top 5 percent within quarter", "additional_budgets": [0.01, 0.10]},
        "refit_policy": "No refit after validation; selected training-period model and validation-fitted calibrator are applied once to locked test",
        "event_evaluation": "Unique validated FDIC closing event; capture if any eligible pre-failure quarter is in same-quarter alert budget",
        "subgroup_evaluation": ["reporting_year", "reporting_quarter", "asset_size_band", "bank_class", "feature_quality_status"],
        "random_seeds": [20260718],
        "statistical_uncertainty": "200 institution-cluster bootstrap draws; event capture resamples unique failure events",
        "test_access_rule": "Exactly one completed access after pre-test manifest, commit and tag",
        "stop_conditions": ["input hash mismatch", "split overlap", "protocol hash mismatch", "pre-test manifest incomplete", "locked-test access already completed", "blocking leakage control failure"],
        "model_features_hash": features["configuration_hash"],
        "model_candidates_hash": candidates["configuration_hash"],
        "evaluation_metrics_hash": metrics["configuration_hash"],
        "locked_test_policy_hash": locked["configuration_hash"],
        "phase3_database_sha256": sha256_file(ROOT / "database/bank_risk_features.duckdb"),
        "phase4_database_sha256": sha256_file(ROOT / "database/bank_risk_labels.duckdb"),
    }, ROOT / "configs/experiment_protocol.yaml")
    paths: tuple[Path, ...] = (
        ROOT / "configs/experiment_protocol.yaml", ROOT / "configs/model_features.yaml",
        ROOT / "configs/model_candidates.yaml", ROOT / "configs/evaluation_metrics.yaml",
        ROOT / "configs/locked_test_policy.yaml",
    )
    manifest: JsonObject = {
        "status": "FROZEN_BEFORE_FINAL_MODEL_FITTING",
        "protocol_version": protocol["version"],
        "protocol_configuration_hash": protocol["configuration_hash"],
        "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(path)} for path in paths],
        "phase3_database_sha256": protocol["phase3_database_sha256"],
        "phase4_database_sha256": protocol["phase4_database_sha256"],
        "preliminary_validation_run": "INVALIDATED_WITHOUT_LOCKED_TEST_ACCESS",
    }
    write_replaceable_json(ROOT / "manifests/model_experiment/protocol_manifest.json", manifest)
    (ROOT / "configs/experiment_protocol.sha256").write_text(str(protocol["configuration_hash"]) + "\n", encoding="utf-8")
    print(protocol["configuration_hash"])


if __name__ == "__main__":
    main()
