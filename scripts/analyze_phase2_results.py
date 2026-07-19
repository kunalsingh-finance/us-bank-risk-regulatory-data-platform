"""Produce focused evidence for Phase 2 identifier and temporal exceptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


QUERIES: dict[str, str] = {
    "rssdid_multi_cert_overlap": """
        WITH mappings AS (
            SELECT rssdid, cert, MIN(reporting_date) AS first_date, MAX(reporting_date) AS last_date
            FROM core.bank_quarter_financials GROUP BY rssdid, cert
        ), multi AS (
            SELECT rssdid FROM mappings GROUP BY rssdid HAVING COUNT(*) > 1
        ), overlapping AS (
            SELECT DISTINCT a.rssdid FROM mappings a JOIN mappings b
              ON a.rssdid = b.rssdid AND a.cert < b.cert
             AND a.first_date <= b.last_date AND b.first_date <= a.last_date
        )
        SELECT (SELECT COUNT(*) FROM multi) AS multi_rssdid,
               (SELECT COUNT(*) FROM overlapping) AS overlapping_rssdid,
               (SELECT COUNT(*) FROM multi WHERE rssdid NOT IN (SELECT rssdid FROM overlapping)) AS sequential_rssdid
    """,
    "post_resolution_timing": """
        SELECT x.resolution_type,
               CASE
                 WHEN DATE_TRUNC('quarter', reporting_date) = DATE_TRUNC('quarter', closing_date)
                 THEN 'same_resolution_quarter'
                 ELSE 'later_quarter'
               END AS timing,
               COUNT(*) AS row_count,
               COUNT(DISTINCT f.cert) AS institution_count
        FROM core.bank_quarter_financials f
        JOIN core.bank_failures_reference x USING (cert)
        WHERE reporting_date > closing_date
        GROUP BY x.resolution_type, timing ORDER BY x.resolution_type, timing
    """,
    "later_quarter_resolution_reference_details": """
        SELECT f.cert, x.institution_name AS resolution_reference_name, x.resolution_type, x.closing_date,
               MIN(f.reporting_date) FILTER (
                   WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
               ) AS first_later_quarter,
               MAX(f.reporting_date) AS last_financial_date,
               COUNT(*) FILTER (
                   WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
               ) AS later_quarter_rows,
               COUNT(DISTINCT f.rssdid) FILTER (
                   WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
               ) AS later_rssdid_count,
               STRING_AGG(DISTINCT f.institution_name, ' | ' ORDER BY f.institution_name) FILTER (
                   WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
               ) AS later_reported_names
        FROM core.bank_quarter_financials f
        JOIN core.bank_failures_reference x USING (cert)
        GROUP BY f.cert, x.institution_name, x.resolution_type, x.closing_date
        HAVING COUNT(*) FILTER (
            WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
        ) > 0
        ORDER BY f.cert
    """,
    "unresolved_history_by_taxonomy": """
        SELECT event_taxonomy, cert_source_field, COUNT(*) AS row_count
        FROM core.institution_history_events WHERE cert IS NULL
        GROUP BY event_taxonomy, cert_source_field ORDER BY row_count DESC
    """,
    "source_matching": """
        SELECT metric, source_identifiers, matched_identifiers, unmatched_identifiers, match_percentage
        FROM reporting.identifier_crosswalk_summary ORDER BY metric
    """,
    "failure_type_matching": """
        SELECT resolution_type, COUNT(*) AS source_records,
               COUNT(*) FILTER (
                   WHERE cert IN (SELECT cert FROM core.bank_quarter_financials)
               ) AS matched_records
        FROM core.bank_failures_reference GROUP BY resolution_type ORDER BY resolution_type
    """,
    "history_reconciliation": """
        SELECT * FROM reporting.history_event_reconciliation ORDER BY event_taxonomy
    """,
    "selected_field_missingness": """
        SELECT COUNT(*) FILTER (WHERE asset IS NULL) AS missing_asset,
               COUNT(*) FILTER (WHERE equity IS NULL) AS missing_equity,
               COUNT(*) FILTER (WHERE assessable_deposits IS NULL) AS missing_assessable_deposits,
               COUNT(*) FILTER (WHERE quarterly_net_interest_margin IS NULL) AS missing_quarterly_nim,
               COUNT(*) FILTER (WHERE quarterly_funding_cost IS NULL) AS missing_quarterly_funding_cost
        FROM core.bank_quarter_financials
    """,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    connection = duckdb.connect(str(arguments.database), read_only=True)
    try:
        payload: dict[str, list[dict[str, object]]] = {}
        for name, query in QUERIES.items():
            relation = connection.sql(query)
            columns: list[str] = relation.columns
            payload[name] = [dict(zip(columns, row, strict=True)) for row in relation.fetchall()]
    finally:
        connection.close()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
