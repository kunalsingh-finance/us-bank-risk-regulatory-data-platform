"""Deterministic SQL report export from the validated DuckDB database."""

from __future__ import annotations

from pathlib import Path

import duckdb

from .manifest import sha256_file


REPORT_QUERIES: dict[str, str] = {
    "sql_source_to_staging_reconciliation.csv": "SELECT * FROM reporting.source_to_staging_reconciliation ORDER BY source_name",
    "sql_staging_to_core_reconciliation.csv": "SELECT * FROM reporting.staging_to_core_reconciliation ORDER BY source_name",
    "identifier_crosswalk_summary.csv": "SELECT * FROM reporting.identifier_crosswalk_summary ORDER BY metric",
    "unmatched_identifier_details.csv": "SELECT * FROM quality.unmatched_identifiers ORDER BY match_type, cert, first_date",
    "failure_financial_history_reconciliation.csv": "SELECT * FROM reporting.failure_financial_history_reconciliation ORDER BY closing_date, cert",
    "history_event_reconciliation.csv": "SELECT * FROM reporting.history_event_reconciliation ORDER BY event_taxonomy",
    "sql_data_quality_summary.csv": "SELECT * FROM reporting.data_quality_summary ORDER BY severity, category",
    "sql_data_quality_exceptions.csv": "SELECT * FROM quality.data_quality_exceptions ORDER BY severity, control_id, cert, reporting_date, exception_id",
}


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def export_reports(database_path: Path, report_dir: Path) -> dict[str, str]:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database does not exist: {database_path}")
    report_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path), read_only=True)
    hashes: dict[str, str] = {}
    try:
        for filename, query in REPORT_QUERIES.items():
            output_path: Path = report_dir / filename
            connection.execute(
                f"COPY ({query}) TO '{sql_path(output_path)}' (FORMAT CSV, HEADER TRUE, DELIMITER ',')"
            )
            hashes[filename] = sha256_file(output_path)
    finally:
        connection.close()
    return hashes

