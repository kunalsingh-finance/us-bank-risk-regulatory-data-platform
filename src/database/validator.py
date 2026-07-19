"""Structural validation for the Phase 2 canonical database."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb


class DatabaseValidationError(RuntimeError):
    """Raised when a blocking database reconciliation fails."""


@dataclass(frozen=True)
class ValidationResult:
    control_name: str
    expected: int
    observed: int
    status: str


def scalar_int(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    value: object = connection.execute(query).fetchone()[0]
    if not isinstance(value, int):
        raise DatabaseValidationError(f"Validation query did not return integer: query={query}, value={value!r}")
    return value


def validate_database(
    connection: duckdb.DuckDBPyConnection,
    expected_financial_rows: int,
    expected_institution_rows: int,
    expected_history_rows: int,
    expected_failure_rows: int,
) -> tuple[ValidationResult, ...]:
    controls: tuple[tuple[str, int, str], ...] = (
        ("staging_financial_rows", expected_financial_rows, "SELECT COUNT(*) FROM staging.financials"),
        ("core_financial_rows", expected_financial_rows, "SELECT COUNT(*) FROM core.bank_quarter_financials"),
        ("core_financial_unique_keys", expected_financial_rows, "SELECT COUNT(DISTINCT (cert, reporting_date)) FROM core.bank_quarter_financials"),
        ("staging_institution_rows", expected_institution_rows, "SELECT COUNT(*) FROM staging.institutions"),
        ("core_institution_rows", expected_institution_rows, "SELECT COUNT(*) FROM core.institutions"),
        ("core_institution_unique_cert", expected_institution_rows, "SELECT COUNT(DISTINCT cert) FROM core.institutions"),
        ("staging_history_rows", expected_history_rows, "SELECT COUNT(*) FROM staging.history_events"),
        ("core_history_rows", expected_history_rows, "SELECT COUNT(*) FROM core.institution_history_events"),
        ("staging_failure_rows", expected_failure_rows, "SELECT COUNT(*) FROM staging.failures"),
        ("core_failure_rows", expected_failure_rows, "SELECT COUNT(*) FROM core.bank_failures_reference"),
        ("core_failure_unique_cert", expected_failure_rows, "SELECT COUNT(DISTINCT cert) FROM core.bank_failures_reference"),
        ("missing_financial_cert", 0, "SELECT COUNT(*) FROM core.bank_quarter_financials WHERE cert IS NULL"),
        ("missing_financial_rssdid", 0, "SELECT COUNT(*) FROM core.bank_quarter_financials WHERE rssdid IS NULL"),
        ("missing_financial_date", 0, "SELECT COUNT(*) FROM core.bank_quarter_financials WHERE reporting_date IS NULL"),
        ("financial_parse_failures", 0, "SELECT COUNT(*) FROM staging.financials WHERE identifier_parse_status <> 'PASS'"),
    )
    results: list[ValidationResult] = []
    failures: list[str] = []
    for name, expected, query in controls:
        observed: int = scalar_int(connection, query)
        status: str = "PASS" if observed == expected else "FAIL"
        results.append(ValidationResult(name, expected, observed, status))
        if status == "FAIL":
            failures.append(f"{name}: expected={expected}, observed={observed}")
    if failures:
        raise DatabaseValidationError("Blocking database controls failed: " + "; ".join(failures))
    return tuple(results)

