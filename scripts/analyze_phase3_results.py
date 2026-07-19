"""Export concise Phase 3 completion evidence as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


QUERIES: dict[str, str] = {
    "feature_rows": "SELECT COUNT(*) AS rows, COUNT(DISTINCT (cert,reporting_date)) AS unique_keys, COUNT(DISTINCT cert) AS institutions, MIN(reporting_date) AS first_date, MAX(reporting_date) AS last_date FROM core.bank_quarter_risk_features",
    "features_by_category": "SELECT financial_category,COUNT(*) AS features FROM audit.feature_inventory GROUP BY 1 ORDER BY 1",
    "exception_severity": "SELECT severity,COUNT(*) AS exceptions FROM quality.feature_exceptions GROUP BY 1 ORDER BY 1",
    "denominator_flags": "SELECT quality_flag,COUNT(*) AS exceptions FROM quality.feature_denominator_exceptions GROUP BY 1 ORDER BY 1",
    "peer_methods": "SELECT peer_group_method,COUNT(*) AS bank_quarters,COUNT(DISTINCT final_peer_group_id) AS groups FROM core.bank_peer_groups GROUP BY 1 ORDER BY 1",
    "benchmark_methods": "SELECT peer_group_method,COUNT(*) AS feature_rows,COUNT(*) FILTER(WHERE peer_feature_count_too_small) AS small_peer_rows FROM core.bank_quarter_peer_benchmarks GROUP BY 1 ORDER BY 1",
    "peer_feature_counts": "SELECT MIN(peer_count) AS minimum,MEDIAN(peer_count) AS median,MAX(peer_count) AS maximum,COUNT(*) FILTER(WHERE peer_count<20) AS small_rows FROM core.bank_quarter_peer_benchmarks",
    "quality_controls": "SELECT * FROM quality.feature_control_results ORDER BY control_id",
    "quality_flag_rows": "SELECT SUM(missing_numerator_count) AS missing_numerator_signals,SUM(denominator_exception_count) AS denominator_signals,COUNT(*) FILTER(WHERE insufficient_lag_history) AS lag_warning_rows,COUNT(*) FILTER(WHERE peer_group_too_small) AS small_group_rows,COUNT(*) FILTER(WHERE extreme_preserved_value) AS extreme_rows,COUNT(*) FILTER(WHERE suspected_unit_issue) AS suspected_unit_rows,COUNT(*) FILTER(WHERE identifier_continuity_concern) AS identifier_rows,COUNT(*) FILTER(WHERE source_field_quality_warning) AS source_warning_rows FROM core.bank_quarter_feature_quality",
    "flag_counts": "SELECT SUM(capital_deterioration_flag),SUM(asset_quality_deterioration_flag),SUM(earnings_deterioration_flag),SUM(liquidity_deterioration_flag),SUM(funding_pressure_flag),SUM(concentration_pressure_flag),SUM(rapid_asset_growth_flag),SUM(rapid_loan_growth_flag),SUM(funding_gap_flag) FROM core.bank_quarter_risk_features",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    connection = duckdb.connect(str(arguments.database), read_only=True)
    payload: dict[str, list[dict[str, object]]] = {}
    try:
        for name, query in QUERIES.items():
            relation = connection.sql(query)
            payload[name] = [dict(zip(relation.columns, row, strict=True)) for row in relation.fetchall()]
    finally:
        connection.close()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
