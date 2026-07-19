"""Deterministic Phase 4 report exports."""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.database.manifest import sha256_file


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def export_label_reports(root: Path, database_path: Path) -> dict[str, str]:
    report_dir: Path = root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    views: dict[str, str] = {
        "failure_event_validation.csv": "failure_event_validation",
        "unmatched_failure_resolution.csv": "unmatched_failure_resolution",
        "assistance_event_validation.csv": "assistance_event_validation",
        "nonfailure_exit_validation.csv": "nonfailure_exit_validation",
        "failure_label_prevalence.csv": "failure_label_prevalence",
        "distress_label_prevalence.csv": "distress_label_prevalence",
        "label_prevalence_by_quarter.csv": "label_prevalence_by_quarter",
        "label_prevalence_by_horizon.csv": "label_prevalence_by_horizon",
        "right_censoring_summary.csv": "right_censoring_summary",
        "competing_risk_summary.csv": "competing_risk_summary",
        "failure_lead_time_distribution.csv": "failure_lead_time_distribution",
        "label_status_summary.csv": "label_status_summary",
        "label_quality_exceptions.csv": "label_quality_exceptions",
        "label_boundary_validation.csv": "label_boundary_validation",
        "manual_label_audit.csv": "manual_label_audit",
        "distress_rule_sensitivity.csv": "distress_rule_sensitivity",
        "class_imbalance_summary.csv": "class_imbalance_summary",
        "label_reconciliation.csv": "label_reconciliation",
        "label_leakage_audit.csv": "label_leakage_audit",
    }
    hashes: dict[str, str] = {}
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path), read_only=True)
    try:
        for filename, view in views.items():
            path: Path = report_dir / filename
            connection.execute(
                f"COPY (SELECT * FROM reporting.{view} ORDER BY ALL) TO '{sql_path(path)}' (FORMAT CSV, HEADER TRUE)"
            )
            hashes[filename] = sha256_file(path)
    finally:
        connection.close()
    return hashes
