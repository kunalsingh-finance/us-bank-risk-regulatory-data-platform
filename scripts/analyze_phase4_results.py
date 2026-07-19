"""Print concise Phase 4 validation statistics for completion reporting."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]


def records(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, object]]:
    cursor: duckdb.DuckDBPyConnection = connection.execute(query)
    columns: tuple[str, ...] = tuple(item[0] for item in cursor.description)
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def main() -> None:
    connection: duckdb.DuckDBPyConnection = duckdb.connect(
        str(ROOT / "database/bank_risk_labels.duckdb"), read_only=True
    )
    queries: dict[str, str] = {
        "failure_events": "SELECT validation_status,COUNT(*) events FROM core.validated_failure_events GROUP BY 1 ORDER BY 1",
        "assistance_events": "SELECT validation_status,COUNT(*) events FROM core.validated_assistance_events GROUP BY 1 ORDER BY 1",
        "nonfailure_exits": "SELECT event_type,COUNT(*) events,COUNT(DISTINCT cert) certs FROM core.validated_nonfailure_exits GROUP BY 1 ORDER BY 1",
        "failure_status": "SELECT * FROM reporting.failure_label_summary ORDER BY horizon,status",
        "distress_status": "SELECT * FROM reporting.distress_label_summary ORDER BY status",
        "distress_sensitivity": "SELECT * FROM reporting.distress_rule_sensitivity",
        "competing_risk": "SELECT * FROM reporting.competing_risk_summary ORDER BY horizon,competing_exit_type",
        "leakage": "SELECT * FROM quality.label_leakage_checks ORDER BY control_id",
        "manual_audit": "SELECT pass_fail,COUNT(*) observations FROM reporting.manual_label_audit GROUP BY 1",
        "controls": "SELECT status,COUNT(*) controls FROM audit.label_control_results GROUP BY 1",
    }
    print(json.dumps({name: records(connection, query) for name, query in queries.items()}, indent=2, default=str))
    connection.close()


if __name__ == "__main__":
    main()
