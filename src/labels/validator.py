"""Blocking Phase 4 label validations."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb


class LabelValidationError(RuntimeError):
    """Raised when a blocking label control fails."""


@dataclass(frozen=True)
class LabelValidationResult:
    control_name: str
    expected: int
    observed: int
    status: str


def scalar_int(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    value: object = connection.execute(query).fetchone()[0]
    if not isinstance(value, int):
        raise LabelValidationError(f"Validation did not return integer: query={query}, value={value!r}")
    return value


def validate_label_database(
    connection: duckdb.DuckDBPyConnection,
    expected_rows: int,
) -> tuple[LabelValidationResult, ...]:
    controls: tuple[tuple[str, int, str], ...] = (
        ("failure_label_rows", expected_rows, "SELECT COUNT(*) FROM core.bank_quarter_failure_labels"),
        ("failure_label_unique_keys", expected_rows, "SELECT COUNT(DISTINCT (cert,reporting_date)) FROM core.bank_quarter_failure_labels"),
        ("distress_label_rows", expected_rows, "SELECT COUNT(*) FROM core.bank_quarter_distress_labels"),
        ("validated_failures", 579, "SELECT COUNT(*) FROM core.validated_failure_events"),
        ("validated_assistance", 13, "SELECT COUNT(*) FROM core.validated_assistance_events"),
        ("unmatched_failures", 8, "SELECT COUNT(*) FROM core.validated_failure_events WHERE validation_status<>'VALIDATED'"),
        ("right_censored_non_null_4q", 0, "SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE right_censored_4q AND failed_within_4_quarters IS NOT NULL"),
        ("right_censored_non_null_8q", 0, "SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE right_censored_8q AND failed_within_8_quarters IS NOT NULL"),
        ("post_event_positives", 0, "SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE (failed_within_4_quarters=1 OR failed_within_8_quarters=1) AND next_failure_date<=reporting_date"),
        ("negative_days", 0, "SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE days_until_failure<0"),
        ("failed_sql_controls", 0, "SELECT COUNT(*) FROM audit.label_control_results WHERE status='FAIL'"),
        ("failed_leakage_controls", 0, "SELECT COUNT(*) FROM quality.label_leakage_checks WHERE status='FAIL'"),
        ("manual_audit_failures", 0, "SELECT COUNT(*) FROM reporting.manual_label_audit WHERE pass_fail='FAIL'"),
    )
    results: list[LabelValidationResult] = []
    failures: list[str] = []
    for name, expected, query in controls:
        observed: int = scalar_int(connection, query)
        status: str = "PASS" if observed == expected else "FAIL"
        results.append(LabelValidationResult(name, expected, observed, status))
        if status == "FAIL":
            failures.append(f"{name}: expected={expected}, observed={observed}")
    if failures:
        raise LabelValidationError("Blocking label controls failed: " + "; ".join(failures))
    return tuple(results)
