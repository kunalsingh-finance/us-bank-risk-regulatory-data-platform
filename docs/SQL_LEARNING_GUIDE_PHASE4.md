# SQL Learning Guide: Phase 4

The label SQL joins each bank-quarter to the next validated event for the same CERT. A closing date must be later than the predictor date; otherwise the row is post-event. `CASE` then applies status precedence so a censored observation cannot accidentally become zero.

Four-quarter and eight-quarter boundaries use calendar intervals, not row counts. This matters when dates are missing. A merger is a competing event because failure can no longer be observed for the same institution after it exits; it is not evidence of financial failure. Assistance is retained separately for the same reason.

Future distress features define an outcome in a separate table. They never become columns in the predictor table. This separation is the practical defense against label leakage.

Five label and leakage-control queries:

```sql
SELECT cert, reporting_date, next_failure_date
FROM core.bank_quarter_label_eligibility
WHERE next_failure_date > reporting_date;
```

```sql
SELECT failure_label_status_4q, COUNT(*)
FROM core.bank_quarter_failure_labels
GROUP BY 1;
```

```sql
SELECT * FROM core.bank_quarter_failure_labels
WHERE right_censored_4q AND failed_within_4_quarters IS NOT NULL;
```

```sql
SELECT competing_exit_type, COUNT(*)
FROM core.bank_quarter_failure_labels
WHERE failure_label_status_4q='CENSORED_NONFAILURE_EXIT'
GROUP BY 1;
```

```sql
SELECT control_id, control_name, status
FROM quality.label_leakage_checks;
```

DuckDB executes the auditable interval, join, and reconciliation logic directly against Parquet-backed regulatory data. Python orchestrates the builds and validations.
