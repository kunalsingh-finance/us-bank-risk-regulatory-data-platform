CREATE TABLE staging.asset_quality_levels AS
SELECT
    cert, reporting_date, quarter_index,
    CASE WHEN gross_loans_leases > 0 AND past_due_30_89 IS NOT NULL THEN 100.0 * past_due_30_89 / gross_loans_leases END AS past_due_30_89_to_total_loans,
    CASE WHEN gross_loans_leases > 0 AND past_due_90_plus IS NOT NULL THEN 100.0 * past_due_90_plus / gross_loans_leases END AS past_due_90_plus_to_total_loans,
    CASE WHEN gross_loans_leases > 0 AND nonaccrual_assets IS NOT NULL THEN 100.0 * nonaccrual_assets / gross_loans_leases END AS nonaccrual_assets_to_total_loans,
    CASE WHEN gross_loans_leases > 0 AND past_due_90_plus IS NOT NULL AND nonaccrual_assets IS NOT NULL
         THEN 100.0 * (past_due_90_plus + nonaccrual_assets) / gross_loans_leases END AS noncurrent_assets_to_total_loans,
    CASE WHEN gross_loans_leases > 0 AND prior_gross_loans > 0 AND quarterly_net_chargeoffs IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 400.0 * quarterly_net_chargeoffs / ((gross_loans_leases + prior_gross_loans) / 2.0) END AS net_chargeoffs_to_average_loans
FROM staging.feature_base;

CREATE TABLE staging.asset_quality_features AS
WITH lagged AS (
    SELECT *,
           LAG(noncurrent_assets_to_total_loans, 1) OVER bank_history AS prior_noncurrent,
           LAG(noncurrent_assets_to_total_loans, 4) OVER bank_history AS year_ago_noncurrent,
           LAG(reporting_date, 1) OVER bank_history AS prior_date,
           LAG(reporting_date, 4) OVER bank_history AS year_ago_date
    FROM staging.asset_quality_levels
    WINDOW bank_history AS (PARTITION BY cert ORDER BY reporting_date)
)
SELECT
    *,
    CASE WHEN prior_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN noncurrent_assets_to_total_loans - prior_noncurrent END AS noncurrent_ratio_change_qoq_pp,
    CASE WHEN year_ago_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN noncurrent_assets_to_total_loans - year_ago_noncurrent END AS noncurrent_ratio_change_yoy_pp,
    CASE WHEN COUNT(noncurrent_assets_to_total_loans) OVER trailing_8 = 8
         THEN REGR_SLOPE(noncurrent_assets_to_total_loans, quarter_index) OVER trailing_8 END AS noncurrent_ratio_slope_8q,
    CASE WHEN COUNT(noncurrent_assets_to_total_loans) OVER trailing_8 = 8
         THEN STDDEV_SAMP(noncurrent_assets_to_total_loans) OVER trailing_8 END AS noncurrent_ratio_volatility_8q,
    CASE WHEN prior_noncurrent IS NULL AND year_ago_noncurrent IS NULL THEN NULL
         WHEN noncurrent_assets_to_total_loans - prior_noncurrent >= 0.50
              OR noncurrent_assets_to_total_loans - year_ago_noncurrent >= 1.00 THEN 1 ELSE 0 END AS asset_quality_deterioration_flag
FROM lagged
WINDOW trailing_8 AS (PARTITION BY cert ORDER BY reporting_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW);
