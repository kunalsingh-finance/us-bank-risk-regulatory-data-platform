"""Read-only DuckDB profiling for Phase 2 source-model design."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]


def rows(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, object]]:
    result = connection.execute(query)
    columns: list[str] = [str(item[0]) for item in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def run() -> None:
    connection = duckdb.connect(":memory:")
    financial_path: str = sql_path(
        ROOT / "data" / "processed" / "ingestion_stage" / "fdic_financials_2001q1_2026q1.parquet"
    )
    institution_path: str = sql_path(ROOT / "data" / "raw" / "fdic_institutions_current.csv")
    history_path: str = sql_path(ROOT / "data" / "raw" / "fdic_history_events_2000_2026.csv")
    failure_path: str = sql_path(ROOT / "data" / "raw" / "fdic_failed_banks_2000_2026.csv")
    connection.execute(f"CREATE VIEW financials AS SELECT * FROM read_parquet('{financial_path}')")
    connection.execute(
        f"CREATE VIEW institutions AS SELECT * FROM read_csv('{institution_path}', header=true, all_varchar=true, strict_mode=true)"
    )
    connection.execute(
        f"CREATE VIEW history AS SELECT * FROM read_csv('{history_path}', header=true, all_varchar=true, strict_mode=true)"
    )
    connection.execute(
        f"CREATE VIEW failures AS SELECT * FROM read_csv('{failure_path}', header=true, all_varchar=true, strict_mode=true)"
    )
    profile: dict[str, object] = {
        "financials": rows(
            connection,
            """
            SELECT count(*) AS rows, count(DISTINCT CERT) AS certs,
                   count(DISTINCT (CERT, REPDTE)) AS bank_quarters,
                   min(REPDTE) AS min_date, max(REPDTE) AS max_date
            FROM financials
            """,
        ),
        "institutions": rows(
            connection,
            """
            SELECT count(*) AS rows, count(DISTINCT CERT) AS certs,
                   count(*) - count(DISTINCT CERT) AS duplicate_certs,
                   count(*) FILTER (WHERE nullif(trim(CERT), '') IS NULL) AS missing_cert,
                   count(*) FILTER (WHERE ACTIVE = '1') AS active_rows,
                   count(DISTINCT FED_RSSD) AS rssdids
            FROM institutions
            """,
        ),
        "history": rows(
            connection,
            """
            SELECT count(*) AS rows, count(DISTINCT ID) AS ids,
                   count(DISTINCT TRANSNUM) AS transnums,
                   count(DISTINCT CERT) AS certs,
                   count(*) FILTER (WHERE nullif(trim(CERT), '') IS NULL) AS missing_cert,
                   min(EFFDATE) AS min_effdate, max(EFFDATE) AS max_effdate
            FROM history
            """,
        ),
        "failures": rows(
            connection,
            """
            SELECT count(*) AS rows, count(DISTINCT ID) AS ids,
                   count(DISTINCT CERT) AS certs,
                   count(*) - count(DISTINCT CERT) AS duplicate_certs,
                   count(*) FILTER (WHERE nullif(trim(CERT), '') IS NULL) AS missing_cert,
                   min(FAILDATE) AS min_faildate_text, max(FAILDATE) AS max_faildate_text
            FROM failures
            """,
        ),
        "history_change_codes": rows(
            connection,
            """
            SELECT CHANGECODE, CHANGECODE_DESC, count(*) AS rows,
                   sum(CASE WHEN VOLUNTARY_LIQUIDATION_FLAG = '1' THEN 1 ELSE 0 END) AS voluntary,
                   sum(CASE WHEN REGAGENT_CHANGE_FLAG = '1' THEN 1 ELSE 0 END) AS regulator_change,
                   sum(CASE WHEN CLASS_CHANGE_FLAG = '1' THEN 1 ELSE 0 END) AS class_change,
                   sum(CASE WHEN FAILED_COM_TO_COM_FLAG = '1' OR FAILED_OTS_TO_COM_FLAG = '1'
                                  OR FAILED_OTS_TO_OTS_FLAG = '1' OR FAILED_OTHER_TO_COM_FLAG = '1'
                                  OR FAILED_RTC_FLAG = '1' THEN 1 ELSE 0 END) AS failure_flags,
                   sum(CASE WHEN ACQ_CERT IS NOT NULL AND trim(ACQ_CERT) <> '' THEN 1 ELSE 0 END) AS acquiring_cert
            FROM history
            GROUP BY CHANGECODE, CHANGECODE_DESC
            ORDER BY rows DESC
            LIMIT 100
            """,
        ),
        "history_flag_totals": rows(
            connection,
            """
            SELECT
              sum(CASE WHEN VOLUNTARY_LIQUIDATION_FLAG = '1' THEN 1 ELSE 0 END) AS voluntary,
              sum(CASE WHEN REGAGENT_CHANGE_FLAG = '1' THEN 1 ELSE 0 END) AS regulator_change,
              sum(CASE WHEN CLASS_CHANGE_FLAG = '1' THEN 1 ELSE 0 END) AS class_change,
              sum(CASE WHEN INSAGENT1_CHANGE_FLAG = '1' THEN 1 ELSE 0 END) AS insurance_change,
              sum(CASE WHEN NEW_CHARTER_FLAG = '1' THEN 1 ELSE 0 END) AS new_charter,
              sum(CASE WHEN WITHDRAW_INSURANCE_COM_FLAG = '1' THEN 1 ELSE 0 END) AS withdraw_insurance,
              sum(CASE WHEN FAILED_COM_TO_COM_FLAG = '1' OR FAILED_OTS_TO_COM_FLAG = '1'
                             OR FAILED_OTS_TO_OTS_FLAG = '1' OR FAILED_OTHER_TO_COM_FLAG = '1'
                             OR FAILED_RTC_FLAG = '1' THEN 1 ELSE 0 END) AS failure_flags,
              sum(CASE WHEN UNASSIST_COM_TO_COM_FLAG = '1' OR UNASSIST_COM_TO_OTS_FLAG = '1'
                             OR UNASSIST_OTS_TO_COM_FLAG = '1' OR UNASSIST_OTS_TO_OTS_FLAG = '1'
                             OR UNASSIST_OTHER_TO_COM_FLAG = '1' THEN 1 ELSE 0 END) AS unassisted_combinations,
              sum(CASE WHEN nullif(trim(ACQ_CERT), '') IS NOT NULL THEN 1 ELSE 0 END) AS acquiring_cert,
              sum(CASE WHEN nullif(trim(OUT_CERT), '') IS NOT NULL THEN 1 ELSE 0 END) AS outgoing_cert,
              sum(CASE WHEN nullif(trim(SUR_CERT), '') IS NOT NULL THEN 1 ELSE 0 END) AS surviving_cert
            FROM history
            """,
        ),
        "cross_source": rows(
            connection,
            """
            WITH f AS (SELECT DISTINCT CERT FROM financials),
                 i AS (SELECT DISTINCT CERT FROM institutions WHERE nullif(trim(CERT), '') IS NOT NULL),
                 h AS (SELECT DISTINCT CERT FROM history WHERE nullif(trim(CERT), '') IS NOT NULL),
                 x AS (SELECT DISTINCT CERT FROM failures WHERE nullif(trim(CERT), '') IS NOT NULL)
            SELECT
              (SELECT count(*) FROM f) AS financial_certs,
              (SELECT count(*) FROM f INNER JOIN i USING (CERT)) AS financial_in_institutions,
              (SELECT count(*) FROM f INNER JOIN h USING (CERT)) AS financial_in_history,
              (SELECT count(*) FROM x) AS failure_certs,
              (SELECT count(*) FROM x INNER JOIN f USING (CERT)) AS failures_in_financials,
              (SELECT count(*) FROM h) AS history_certs,
              (SELECT count(*) FROM h INNER JOIN f USING (CERT)) AS history_in_financials
            """,
        ),
        "failure_samples": rows(
            connection,
            "SELECT CERT, NAME, FAILDATE, BIDNAME, FUND, FIN, ID FROM failures ORDER BY ID LIMIT 10",
        ),
        "institution_samples": rows(
            connection,
            "SELECT CERT, FED_RSSD, NAME, CITY, STALP, BKCLASS, REGAGNT, ESTYMD, INACTIVE, ACTIVE, ASSET, REPDTE, RISDATE FROM institutions ORDER BY CERT LIMIT 10",
        ),
    }
    output_path: Path = ROOT / "reports" / "phase2_source_profile.json"
    output_path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(profile, indent=2, sort_keys=True))


if __name__ == "__main__":
    run()
