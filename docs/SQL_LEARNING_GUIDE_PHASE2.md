# SQL Learning Guide — Phase 2

This phase uses DuckDB as an embedded analytical database: it reads Parquet/CSV directly, runs standard SQL locally, and produces a single reproducible database file. The design separates source-preserving staging, canonical analytical tables, and quality-control evidence.

## Core ideas

Staging tables preserve source columns and add parse status. They create an audit boundary: source text can be compared with typed values without editing the source. Core tables then expose stable names and types. The canonical key is `(CERT, reporting_date)` because a bank can appear in many quarters and a quarter contains many banks.

`LEFT JOIN` keeps every row from the left table and shows missing matches as null; this is essential for reconciliation. `INNER JOIN` keeps only matched rows and is useful for counting coverage, but would silently discard unmatched historical banks if used to build the fact. CTEs (`WITH` clauses) name intermediate result sets so matching and control logic can be reviewed in steps. `GROUP BY` converts detailed rows into counts or ranges. `CASE` translates traceable source evidence into a descriptive taxonomy.

Window functions examine neighboring rows without collapsing them. Phase 2 avoids feature lags, but later phases may use `LAG()` for quarter-over-quarter movement only after ordering by bank and date. Exception queries select rule violations into a table rather than deleting them.

## Five validation queries

1. Prove the bank-quarter key is unique:

```sql
SELECT COUNT(*) AS rows,
       COUNT(DISTINCT (cert, reporting_date)) AS unique_keys
FROM core.bank_quarter_financials;
```

Both results must be 698,804.

2. Reconcile current-reference coverage with a `LEFT JOIN`:

```sql
SELECT COUNT(DISTINCT f.cert) AS financial_banks,
       COUNT(DISTINCT i.cert) AS matched_current_banks
FROM core.bank_quarter_financials f
LEFT JOIN core.institutions i USING (cert);
```

The six unmatched CERTs remain in the fact because the current file is not a complete historical dimension.

3. Summarize quarterly coverage:

```sql
SELECT reporting_date, COUNT(*) AS banks
FROM core.bank_quarter_financials
GROUP BY reporting_date
ORDER BY reporting_date;
```

This is a reconciliation query, not a risk feature.

4. Explain event taxonomy with `CASE`:

```sql
SELECT event_code,
       CASE
         WHEN event_code IN ('211','215','216','217','230') THEN 'Failure-related'
         WHEN event_code IN ('221','222','223','224','810','811') THEN 'Merger'
         WHEN event_code = '510' THEN 'Name change'
         ELSE 'Other'
       END AS event_group
FROM staging.history_events;
```

The production query also uses official flags and retains every raw code.

5. Read the control inventory and exception counts:

```sql
SELECT control_id, control_name, severity,
       exception_count, control_status
FROM quality.control_results
ORDER BY control_id;
```

An exception is evidence to investigate, not a row to delete.

## Design summary

DuckDB queries Parquet and CSV directly with SQL and creates a portable analytical database. Source-preserving staging tables are separate from canonical core tables. CERT plus quarter-end date forms the fact key, left joins retain unmatched records, and separate audit, lineage, reconciliation, and exception tables preserve control evidence. Python orchestrates the ordered, transactional SQL build.

Institution names are not stable keys, and current institution data cannot be forward-filled historically. Assistance records remain distinct from failures. The 56 sequential RSSDID mappings represent changes over time rather than concurrent identifier conflicts.
