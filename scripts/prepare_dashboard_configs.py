"""Freeze deterministic Phase 6 dashboard configurations."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, configuration_hash, load_json_object, sha256_file, write_replaceable_json  # noqa: E402


def freeze(payload: JsonObject, path: Path) -> JsonObject:
    frozen: JsonObject = dict(payload)
    frozen["configuration_hash"] = configuration_hash(payload)
    write_replaceable_json(path, frozen)
    return frozen


def main() -> None:
    protocol: JsonObject = load_json_object(ROOT / "configs/experiment_protocol.yaml")
    selection: JsonObject = load_json_object(ROOT / "manifests/model_experiment/pre_test_selection_manifest.json")
    reports: JsonObject = load_json_object(ROOT / "manifests/model_experiment/report_hashes.json")
    model_artifact: Path = ROOT / str(selection["outcome_selections"]["failure_4q"]["model_path"])  # type: ignore[index]
    history_features: list[str] = [
        "equity_to_assets", "equity_change_yoy_pct", "noncurrent_assets_to_total_loans",
        "past_due_30_89_to_total_loans", "return_on_assets", "return_on_equity",
        "net_interest_margin", "efficiency_ratio", "liquid_assets_to_total_assets",
        "loans_to_deposits", "deposits_to_total_assets", "fhlb_advances_to_total_assets",
        "deposit_growth_yoy_pct", "funding_cost", "loan_concentration_hhi",
        "largest_reported_loan_category_share", "total_asset_growth_yoy_pct",
        "total_loan_growth_yoy_pct", "loan_growth_minus_deposit_growth",
    ]
    explanation_features: list[str] = [
        "equity_to_assets", "equity_change_yoy_pct", "equity_change_qoq_pct",
        "total_asset_growth_qoq_pct", "return_on_equity", "equity_to_assets_volatility_8q",
        "total_loan_growth_yoy_pct", "loans_to_deposits", "past_due_30_89_to_total_loans",
        "roa_volatility_8q",
    ]
    dashboard: JsonObject = freeze({
        "version": "phase6-dashboard-v1",
        "dashboard_build_run_id": "phase6-dashboard-v1-20260718",
        "build_timestamp": "2026-07-18T18:00:00Z",
        "frozen_model_version": str(selection["selected_model"]),
        "protocol_hash": str(protocol["configuration_hash"]),
        "feature_contract_hash": str(protocol["model_features_hash"]),
        "phase3_database_sha256": str(protocol["phase3_database_sha256"]),
        "phase4_database_sha256": str(protocol["phase4_database_sha256"]),
        "phase5_model_database_sha256": sha256_file(ROOT / "database/bank_risk_models.duckdb"),
        "model_artifact_path": str(model_artifact.relative_to(ROOT)).replace("\\", "/"),
        "model_artifact_sha256": sha256_file(model_artifact),
        "phase5_report_hash_manifest_sha256": sha256_file(ROOT / "manifests/model_experiment/report_hashes.json"),
        "phase5_report_hashes": reports["report_hashes"],
        "prediction_outcome": "failure_4q",
        "primary_monitoring_budget": 0.05,
        "secondary_alert_budgets": [0.01, 0.10],
        "history_features": history_features,
        "peer_features": explanation_features,
        "explanation_features": explanation_features,
        "presentation_directory": "data/processed/dashboard",
        "dashboard_directory": "dashboards",
        "supported_prediction_splits": ["VALIDATION", "LOCKED_TEST"],
        "minimum_peer_count": 20,
        "local_explanation_method": "single-feature training-median perturbation on frozen model",
        "logical_sort_key": ["reporting_date", "cert"],
    }, ROOT / "configs/dashboard.yaml")
    tiers: JsonObject = freeze({
        "version": "phase6-risk-tiers-v1",
        "percentile_scale": "0_to_100_same_quarter",
        "tie_method": "shared percentile and shared rank; CERT ascending breaks ties only at fixed alert-budget cutoff",
        "primary_monitoring_budget": 0.05,
        "tiers": [
            {"display_name": "Low", "lower_inclusive": 0.0, "upper_exclusive": 50.0, "interpretation": "Below-median relative indicators", "permitted_wording": "Lower relative ranking", "prohibited_wording": "Safe institution", "top_5_relationship": "Outside top-5% monitoring"},
            {"display_name": "Moderate", "lower_inclusive": 50.0, "upper_exclusive": 90.0, "interpretation": "Between median and 90th percentile", "permitted_wording": "Monitor relative indicators", "prohibited_wording": "Regulatory grade", "top_5_relationship": "Outside top-5% monitoring"},
            {"display_name": "Elevated", "lower_inclusive": 90.0, "upper_exclusive": 95.0, "interpretation": "Elevated same-quarter public-data indicators", "permitted_wording": "Elevated indicators", "prohibited_wording": "Likely to fail", "top_5_relationship": "Immediately below primary monitoring cutoff"},
            {"display_name": "High", "lower_inclusive": 95.0, "upper_exclusive": 99.0, "interpretation": "Top-5% relative indicators", "permitted_wording": "Top-5% review", "prohibited_wording": "Unsafe institution", "top_5_relationship": "Inside primary monitoring population"},
            {"display_name": "Highest monitored tier", "lower_inclusive": 99.0, "upper_exclusive": 100.000001, "interpretation": "Top-1% relative indicators", "permitted_wording": "Highest monitored ranking tier", "prohibited_wording": "Will fail", "top_5_relationship": "Inside top-1% and top-5% monitoring populations"},
        ],
        "limitations": "Tiers are relative same-quarter rankings and do not represent calibrated event likelihoods.",
    }, ROOT / "configs/dashboard_risk_tiers.yaml")
    cases: JsonObject = freeze({
        "version": "phase6-case-studies-v1",
        "selection_frozen_before_dashboard_review": True,
        "roles": [
            {"role": "Short-lead captured failure", "rule": "minimum positive top-5% lead days"},
            {"role": "Long-lead captured failure", "rule": "maximum top-5% lead days"},
            {"role": "Top-1% captured failure", "rule": "maximum score among top-1% captured events"},
            {"role": "Top-5% not top-1% captured failure", "rule": "first qualifying event; unavailable record required if none"},
            {"role": "Missed failure", "rule": "earliest event missed at top 10%"},
            {"role": "False-positive high-ranking institution", "rule": "highest locked-test score among negative observations"},
            {"role": "Small-bank case", "rule": "first captured event in sub-$500M band not already selected"},
            {"role": "Larger-bank case", "rule": "largest asset-band positive event available"},
        ],
        "prohibit_success_only_selection": True,
    }, ROOT / "configs/dashboard_case_studies.yaml")
    disclaimers: JsonObject = freeze({
        "version": "phase6-disclaimers-v1",
        "persistent": "This platform ranks institutions relative to other eligible banks in the same reporting quarter using public FDIC data. Scores are not calibrated failure probabilities, official CAMELS ratings, regulatory determinations, or investment recommendations.",
        "bank_detail": "An elevated ranking indicates stronger public-data risk indicators relative to peers. It does not mean that the institution will fail.",
        "ranking_interpretation": "An elevated ranking indicates stronger public-data risk indicators relative to other eligible institutions in the same reporting quarter. It does not mean that the institution will fail.",
        "driver_heading": "Factors associated with the institution's model ranking",
    }, ROOT / "configs/dashboard_disclaimers.yaml")
    print(f"PASS dashboard={dashboard['configuration_hash']} tiers={tiers['configuration_hash']} cases={cases['configuration_hash']} disclaimers={disclaimers['configuration_hash']}")


if __name__ == "__main__":
    main()
