"""Deterministic Phase 3 report exports."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from src.database.manifest import JsonObject, load_json_object, sha256_file


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def copy_query(connection: duckdb.DuckDBPyConnection, query: str, path: Path) -> str:
    connection.execute(f"COPY ({query}) TO '{sql_path(path)}' (FORMAT CSV, HEADER TRUE)")
    return sha256_file(path)


def feature_names(config: JsonObject) -> tuple[str, ...]:
    raw: object = config["features"]
    if not isinstance(raw, list):
        raise ValueError("features must be a list")
    return tuple(str(item["feature_name"]) for item in raw if isinstance(item, dict))


def unpivot_query(names: tuple[str, ...]) -> str:
    columns: str = ",".join(names)
    return (
        "SELECT cert, reporting_date, feature_name, feature_value "
        "FROM core.bank_quarter_risk_features "
        f"UNPIVOT (feature_value FOR feature_name IN ({columns}))"
    )


def write_inventory(
    connection: duckdb.DuckDBPyConnection,
    config: JsonObject,
    path: Path,
) -> str:
    raw: object = config["features"]
    if not isinstance(raw, list):
        raise ValueError("features must be a list")
    with path.open("w", encoding="utf-8", newline="") as handle:
        columns: list[str] = [
            "feature_name", "category", "formula", "numerator", "denominator", "units", "source_fields",
            "first_available_quarter", "last_available_quarter", "non_null_count", "missing_percentage",
            "risk_direction", "trend_windows", "peer_benchmark_status", "known_limitations", "downstream_eligibility",
        ]
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError(f"Invalid feature item: {item!r}")
            name: str = str(item["feature_name"])
            stats: tuple[object, ...] = connection.execute(
                f"SELECT MIN(reporting_date) FILTER (WHERE {name} IS NOT NULL), "
                f"MAX(reporting_date) FILTER (WHERE {name} IS NOT NULL), COUNT({name}), "
                f"100.0 * COUNT(*) FILTER (WHERE {name} IS NULL) / COUNT(*) "
                "FROM core.bank_quarter_risk_features"
            ).fetchone()
            writer.writerow({
                "feature_name": name, "category": item["financial_category"], "formula": item["formula"],
                "numerator": item["numerator"], "denominator": item["denominator"], "units": item["units"],
                "source_fields": f"{item['numerator']} | {item['denominator']}",
                "first_available_quarter": stats[0], "last_available_quarter": stats[1],
                "non_null_count": stats[2], "missing_percentage": stats[3],
                "risk_direction": item["direction_of_risk"], "trend_windows": "|".join(item["trend_windows"]),
                "peer_benchmark_status": item["peer_group_requirement"] != "None",
                "known_limitations": item["known_limitation"],
                "downstream_eligibility": item["allowed_downstream_use"],
            })
    return sha256_file(path)


def export_feature_reports(root: Path, database_path: Path, config_path: Path) -> dict[str, str]:
    report_dir: Path = root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    config: JsonObject = load_json_object(config_path)
    names: tuple[str, ...] = feature_names(config)
    values: str = unpivot_query(names)
    connection = duckdb.connect(str(database_path), read_only=True)
    hashes: dict[str, str] = {}
    try:
        hashes["feature_inventory.csv"] = write_inventory(connection, config, report_dir / "feature_inventory.csv")
        queries: dict[str, str] = {
            "feature_availability_by_quarter.csv": f"WITH v AS ({values}), q AS (SELECT DISTINCT reporting_date FROM core.bank_quarter_risk_features), n AS (SELECT feature_name FROM audit.feature_inventory), a AS (SELECT reporting_date,feature_name,COUNT(*) AS non_null_count FROM v GROUP BY 1,2) SELECT q.reporting_date,n.feature_name,COALESCE(a.non_null_count,0) AS non_null_count FROM q CROSS JOIN n LEFT JOIN a USING(reporting_date,feature_name) ORDER BY 1,2",
            "feature_missingness_by_quarter.csv": f"WITH v AS ({values}), q AS (SELECT reporting_date, COUNT(*) AS banks FROM core.bank_quarter_risk_features GROUP BY 1), n AS (SELECT feature_name FROM audit.feature_inventory), a AS (SELECT reporting_date,feature_name,COUNT(*) AS non_null_count FROM v GROUP BY 1,2) SELECT q.reporting_date,n.feature_name,q.banks-COALESCE(a.non_null_count,0) AS missing_count,100.0*(q.banks-COALESCE(a.non_null_count,0))/q.banks AS missing_percentage FROM q CROSS JOIN n LEFT JOIN a USING(reporting_date,feature_name) ORDER BY 1,2",
            "feature_distribution_summary.csv": f"SELECT feature_name, COUNT(*) AS non_null_count, MIN(feature_value) AS minimum, QUANTILE_CONT(feature_value,0.01) AS p01, QUANTILE_CONT(feature_value,0.05) AS p05, MEDIAN(feature_value) AS median, QUANTILE_CONT(feature_value,0.95) AS p95, QUANTILE_CONT(feature_value,0.99) AS p99, MAX(feature_value) AS maximum, COUNT(*) FILTER(WHERE NOT ISFINITE(feature_value)) AS infinity_count FROM ({values}) GROUP BY feature_name ORDER BY feature_name",
            "feature_extreme_value_summary.csv": "SELECT feature_name, quality_flag, COUNT(*) AS exception_count FROM quality.feature_exceptions WHERE category='Extreme value' GROUP BY 1,2 ORDER BY 1,2",
            "feature_denominator_exceptions.csv": "SELECT * FROM quality.feature_denominator_exceptions ORDER BY feature_name,cert,reporting_date",
            "feature_quality_summary.csv": "SELECT * FROM reporting.feature_quality_summary ORDER BY quality_flag",
            "feature_quality_exceptions.csv": "SELECT * FROM quality.feature_exceptions ORDER BY severity,feature_name,cert,reporting_date",
            "peer_group_size_summary.csv": "SELECT * FROM reporting.peer_group_size_summary ORDER BY reporting_date,asset_size_band,peer_group_method",
            "peer_benchmark_validation.csv": "SELECT reporting_date,feature_name,COUNT(*) AS rows,MIN(peer_count) AS min_peer_count,MAX(peer_count) AS max_peer_count,MIN(bank_percentile) AS min_percentile,MAX(bank_percentile) AS max_percentile,COUNT(*) FILTER(WHERE peer_feature_count_too_small) AS small_peer_rows FROM core.bank_quarter_peer_benchmarks GROUP BY 1,2 ORDER BY 1,2",
            "risk_feature_reconciliation.csv": "SELECT * FROM reporting.risk_feature_reconciliation",
            "feature_temporal_validation.csv": "SELECT * FROM reporting.feature_temporal_validation",
        }
        for filename, query in queries.items():
            hashes[filename] = copy_query(connection, query, report_dir / filename)
    finally:
        connection.close()
    return hashes
