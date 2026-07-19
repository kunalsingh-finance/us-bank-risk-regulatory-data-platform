"""Blocking Phase 3 feature-layer validations."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb


class FeatureValidationError(RuntimeError):
    """Raised when a blocking feature control fails."""


@dataclass(frozen=True)
class FeatureValidationResult:
    control_name: str
    expected: int
    observed: int
    status: str


def scalar_int(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    value: object = connection.execute(query).fetchone()[0]
    if not isinstance(value, int):
        raise FeatureValidationError(f"Validation query did not return integer: query={query}, value={value!r}")
    return value


def validate_feature_database(
    connection: duckdb.DuckDBPyConnection,
    expected_rows: int,
    expected_feature_count: int,
) -> tuple[FeatureValidationResult, ...]:
    controls: tuple[tuple[str, int, str], ...] = (
        ("feature_rows", expected_rows, "SELECT COUNT(*) FROM core.bank_quarter_risk_features"),
        ("feature_unique_keys", expected_rows, "SELECT COUNT(DISTINCT (cert, reporting_date)) FROM core.bank_quarter_risk_features"),
        ("quality_rows", expected_rows, "SELECT COUNT(*) FROM core.bank_quarter_feature_quality"),
        ("peer_group_rows", expected_rows, "SELECT COUNT(*) FROM core.bank_peer_groups"),
        ("missing_feature_cert", 0, "SELECT COUNT(*) FROM core.bank_quarter_risk_features WHERE cert IS NULL"),
        ("future_lag_dates", 0, "SELECT COUNT(*) FROM staging.feature_base WHERE prior_reporting_date >= reporting_date OR year_ago_reporting_date >= reporting_date"),
        ("invalid_percentiles", 0, "SELECT COUNT(*) FROM core.bank_quarter_peer_benchmarks WHERE bank_percentile NOT BETWEEN 0 AND 1 OR risk_direction_adjusted_percentile NOT BETWEEN 0 AND 1"),
        ("failed_sql_controls", 0, "SELECT COUNT(*) FROM quality.feature_control_results WHERE status = 'FAIL' AND blocking"),
        ("configured_features", expected_feature_count, "SELECT COUNT(*) FROM audit.feature_inventory"),
    )
    failures: list[str] = []
    results: list[FeatureValidationResult] = []
    for name, expected, query in controls:
        observed: int = scalar_int(connection, query)
        status: str = "PASS" if observed == expected else "FAIL"
        results.append(FeatureValidationResult(name, expected, observed, status))
        if status == "FAIL":
            failures.append(f"{name}: expected={expected}, observed={observed}")
    if failures:
        raise FeatureValidationError("Blocking feature controls failed: " + "; ".join(failures))
    return tuple(results)
