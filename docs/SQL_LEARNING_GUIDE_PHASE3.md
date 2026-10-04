# SQL Learning Guide — Phase 3

Ratios use `CASE` so invalid denominators become null. `LAG(value, 1)` retrieves the preceding quarter and `LAG(value, 4)` retrieves the year-ago row, but the SQL also verifies the exact dates. A trailing window such as `ROWS BETWEEN 7 PRECEDING AND CURRENT ROW` uses only available history; a centered window would leak future observations.

Peer percentiles partition by reporting date, final peer group, and feature. `PERCENT_RANK()` places a bank from 0 to 1 within that historical peer population. `CASE` reverses low-is-risky measures such as capital and ROA. Raw extremes remain unchanged, while quality tables explain why a value is missing or unusual.

Five feature and control queries:

```sql
-- 1. Protected accounting capital ratio
SELECT CASE WHEN asset > 0 THEN 100.0 * equity / asset END AS equity_to_assets
FROM staging.feature_source;
```

```sql
-- 2. Exact year-over-year growth
SELECT CASE WHEN year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
            AND ABS(year_ago_asset) > 0
       THEN 100.0 * (asset - year_ago_asset) / ABS(year_ago_asset) END
FROM staging.feature_base;
```

```sql
-- 3. Backward-looking rolling volatility
SELECT STDDEV_SAMP(return_on_assets) OVER (
  PARTITION BY cert ORDER BY reporting_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
) FROM staging.earnings_levels;
```

```sql
-- 4. Same-quarter peer percentile
SELECT PERCENT_RANK() OVER (
  PARTITION BY reporting_date, final_peer_group_id, feature_name ORDER BY feature_value
) FROM staging.peer_feature_grouped;
```

```sql
-- 5. Audit quality before using a feature
SELECT quality_flag, COUNT(*)
FROM quality.feature_exceptions
GROUP BY quality_flag;
```

The feature SQL applies explicit denominator guards, exact-date lags, backward-looking windows, and quarter-specific peer percentiles. Raw extremes remain preserved, and separately stored quality evidence makes nulls and warnings auditable.
