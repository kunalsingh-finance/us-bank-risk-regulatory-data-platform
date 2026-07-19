from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]


def main() -> None:
    connection = duckdb.connect(str(ROOT / "database/bank_risk_labels.duckdb"), read_only=True)
    for table in ("core.bank_quarter_failure_labels", "core.bank_quarter_distress_labels"):
        print(table)
        print(connection.execute(f"DESCRIBE {table}").fetchall())
    print(
        connection.execute(
            """
            SELECT year(reporting_date) AS year,
                   count(*) FILTER (WHERE failure_label_status_4q = 'POSITIVE') AS positives,
                   count(*) FILTER (WHERE failure_label_status_4q = 'NEGATIVE') AS negatives
            FROM core.bank_quarter_failure_labels
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
    )
    print(
        connection.execute(
            """
            SELECT CASE WHEN reporting_date <= DATE '2013-12-31' THEN 'train'
                        WHEN reporting_date <= DATE '2018-12-31' THEN 'validation'
                        WHEN reporting_date <= DATE '2024-12-31' THEN 'locked_test'
                        ELSE 'outside' END AS split,
                   COUNT(*) FILTER (WHERE failure_label_status_4q IN ('POSITIVE','NEGATIVE')) AS eligible_rows,
                   COUNT(*) FILTER (WHERE failure_label_status_4q='POSITIVE') AS positive_rows,
                   COUNT(DISTINCT cert) FILTER (WHERE failure_label_status_4q='POSITIVE') AS positive_banks
            FROM core.bank_quarter_failure_labels
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
    )
    print(
        connection.execute(
            """SELECT YEAR(closing_date), COUNT(*)
               FROM core.validated_failure_events
               WHERE validation_status='VALIDATED'
               GROUP BY 1 ORDER BY 1"""
        ).fetchall()
    )
    connection.close()
    features = duckdb.connect(str(ROOT / "database/bank_risk_features.duckdb"), read_only=True)
    print(features.execute("DESCRIBE core.bank_quarter_risk_features").fetchall())
    features.close()


if __name__ == "__main__":
    main()
