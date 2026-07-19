"""Inspect immutable Phase 2 and Phase 3 inputs needed for label design."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]
PHASE2: Path = ROOT / "database/bank_risk.duckdb"
PHASE3: Path = ROOT / "database/bank_risk_features.duckdb"


def describe(connection: duckdb.DuckDBPyConnection, table: str) -> list[dict[str, object]]:
    rows: list[tuple[object, ...]] = connection.execute(f"DESCRIBE {table}").fetchall()
    return [{"column": row[0], "type": row[1]} for row in rows]


def query_records(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, object]]:
    cursor: duckdb.DuckDBPyConnection = connection.execute(query)
    columns: tuple[str, ...] = tuple(item[0] for item in cursor.description)
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def main() -> None:
    connection: duckdb.DuckDBPyConnection = duckdb.connect()
    phase2_path: str = str(PHASE2).replace("\\", "/").replace("'", "''")
    phase3_path: str = str(PHASE3).replace("\\", "/").replace("'", "''")
    connection.execute(f"ATTACH '{phase2_path}' AS p2 (READ_ONLY)")
    connection.execute(f"ATTACH '{phase3_path}' AS p3 (READ_ONLY)")
    tables: tuple[str, ...] = (
        "p2.core.bank_quarter_financials",
        "p2.core.bank_failures_reference",
        "p2.core.bank_exits_reference",
        "p2.core.institution_history_events",
        "p2.core.institutions",
        "p3.core.bank_quarter_risk_features",
        "p3.core.bank_quarter_feature_quality",
        "p3.core.bank_peer_groups",
    )
    output: dict[str, object] = {"schemas": {table: describe(connection, table) for table in tables}}
    output["failure_reconciliation"] = query_records(connection,
        """SELECT resolution_type, COUNT(*) AS events,
                  COUNT(*) FILTER (WHERE f.cert IS NOT NULL) AS matched
           FROM p2.core.bank_failures_reference x
           LEFT JOIN (SELECT DISTINCT cert FROM p2.core.bank_quarter_financials) f USING (cert)
           GROUP BY resolution_type ORDER BY resolution_type"""
    )
    output["unmatched_failures"] = query_records(connection,
        """SELECT x.failure_record_id, x.cert, x.institution_name, x.city, x.state,
                  x.closing_date, x.fund_number, x.source_record_reference
           FROM p2.core.bank_failures_reference x
           LEFT JOIN (SELECT DISTINCT cert FROM p2.core.bank_quarter_financials) f USING (cert)
           WHERE x.resolution_type = 'FAILURE' AND f.cert IS NULL
           ORDER BY x.closing_date, x.cert"""
    )
    output["exit_counts"] = query_records(connection,
        """SELECT exit_classification, COUNT(*) AS rows, COUNT(DISTINCT cert) AS certs
           FROM p2.core.bank_exits_reference GROUP BY exit_classification ORDER BY 1"""
    )
    print(json.dumps(output, indent=2, default=str))
    connection.close()


if __name__ == "__main__":
    main()
