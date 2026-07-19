"""Freeze Phase 4 outcome-label configurations and their hashes."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import configuration_hash, sha256_file, write_replaceable_json  # noqa: E402


def freeze(payload: dict[str, object], path: Path) -> None:
    frozen: dict[str, object] = dict(payload)
    frozen["configuration_hash"] = configuration_hash(frozen)
    write_replaceable_json(path, frozen)


def main() -> None:
    protocol_path: Path = ROOT / "docs/LABEL_DEVELOPMENT_PROTOCOL.md"
    phase2_path: Path = ROOT / "database/bank_risk.duckdb"
    phase3_path: Path = ROOT / "database/bank_risk_features.duckdb"
    labels: list[dict[str, object]] = []
    for quarters in (4, 8):
        labels.append({
            "label_name": f"failed_within_{quarters}_quarters",
            "outcome_type": "Validated FDIC failure",
            "horizon": f"{quarters} quarters",
            "event_source": "phase2.core.bank_failures_reference where resolution_type=FAILURE",
            "event_date_field": "closing_date",
            "positive_condition": "closing_date > reporting_date and closing_date <= inclusive horizon boundary",
            "negative_condition": "complete surveillance window with no prior failure or competing non-failure exit",
            "censoring_rule": "null binary label for incomplete surveillance window",
            "competing_risk_rule": "earlier non-failure exit within horizon is CENSORED_NONFAILURE_EXIT",
            "required_future_observation_period": f"{quarters} complete quarters",
            "bank_quarter_eligibility_rule": "at least four historical observations and no post-event or blocking quality status",
            "boundary_date_treatment": "inclusive end boundary; reporting-date event is post-event",
            "missing_event_treatment": "absence is negative only with a complete surveillance window",
            "allowed_use": "Primary chronological rare-event modelling after Phase 5 approval",
            "known_limitation": "FDIC failures only; competing exits and assistance are not positives",
            "configuration_version": "phase4-labels-v1",
        })
    freeze({
        "version": "phase4-labels-v1",
        "run_id": "phase4-20260716t235000z",
        "build_timestamp": "2026-07-16T23:50:00Z",
        "phase2_database": "database/bank_risk.duckdb",
        "phase2_database_sha256": sha256_file(phase2_path),
        "phase3_database": "database/bank_risk_features.duckdb",
        "phase3_database_sha256": sha256_file(phase3_path),
        "output_database": "database/bank_risk_labels.duckdb",
        "expected_rows": 698804,
        "panel_start_date": "2001-03-31",
        "panel_end_date": "2026-03-31",
        "event_surveillance_end_date": "2026-07-15",
        "minimum_history_observations": 4,
        "protocol_path": "docs/LABEL_DEVELOPMENT_PROTOCOL.md",
        "protocol_sha256": sha256_file(protocol_path),
        "allowed_statuses": [
            "POSITIVE", "NEGATIVE", "RIGHT_CENSORED", "CENSORED_NONFAILURE_EXIT",
            "INELIGIBLE_POST_EVENT", "INELIGIBLE_DATA_QUALITY",
            "INELIGIBLE_INSUFFICIENT_HISTORY", "UNRESOLVED_EVENT_MAPPING",
        ],
        "labels": labels,
        "sql_execution_order": [
            "sql/phase4/001_create_label_tables.sql",
            "sql/phase4/002_validate_failure_events.sql",
            "sql/phase4/003_validate_assistance_events.sql",
            "sql/phase4/004_validate_nonfailure_exits.sql",
            "sql/phase4/005_build_label_eligibility.sql",
            "sql/phase4/006_build_failure_labels.sql",
            "sql/phase4/007_build_distress_events.sql",
            "sql/phase4/008_build_distress_labels.sql",
            "sql/phase4/009_run_label_quality_controls.sql",
            "sql/phase4/010_create_label_reporting_views.sql",
            "sql/phase4/011_build_report_views.sql",
        ],
    }, ROOT / "configs/outcome_labels.yaml")
    freeze({
        "version": "phase4-distress-v1",
        "primary_label": "severe_deterioration_within_4_quarters",
        "horizon_quarters": 4,
        "minimum_category_count": 2,
        "minimum_history_observations": 4,
        "capital_severe_equity_to_assets_max": 2.0,
        "capital_severe_yoy_change_max": -4.0,
        "capital_evidence_equity_to_assets_max": 5.0,
        "capital_evidence_yoy_change_max": -2.0,
        "asset_quality_noncurrent_ratio_min": 5.0,
        "asset_quality_yoy_change_min": 2.0,
        "earnings_roa_max": -1.0,
        "earnings_minimum_consecutive_losses": 2,
        "liquidity_deposit_outflow_min": 10.0,
        "liquidity_loans_to_deposits_min": 100.0,
        "liquidity_fhlb_to_assets_min": 10.0,
        "categories": {
            "capital": ["capital_deterioration_flag"],
            "asset_quality": ["asset_quality_deterioration_flag"],
            "earnings": ["earnings_deterioration_flag"],
            "liquidity_funding": ["liquidity_deterioration_flag", "funding_pressure_flag"],
        },
        "conditional_features": [],
        "unsupported_features": ["uninsured_deposits_to_total_deposits", "brokered_deposits_to_total_deposits"],
        "selection_policy": "Frozen before modelling; never selected from model performance",
        "methodology_path": "docs/DISTRESS_LABEL_METHODOLOGY.md",
        "methodology_sha256": sha256_file(ROOT / "docs/DISTRESS_LABEL_METHODOLOGY.md"),
    }, ROOT / "configs/distress_labels.yaml")


if __name__ == "__main__":
    main()
