CREATE TABLE staging.growth_features AS
SELECT
    cert, reporting_date,
    CASE WHEN prior_asset IS NOT NULL AND ABS(prior_asset) > 0 AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 100.0 * (asset - prior_asset) / ABS(prior_asset) END AS total_asset_growth_qoq_pct,
    CASE WHEN year_ago_asset IS NOT NULL AND ABS(year_ago_asset) > 0 AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * (asset - year_ago_asset) / ABS(year_ago_asset) END AS total_asset_growth_yoy_pct,
    CASE WHEN prior_gross_loans IS NOT NULL AND ABS(prior_gross_loans) > 0 AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 100.0 * (gross_loans_leases - prior_gross_loans) / ABS(prior_gross_loans) END AS total_loan_growth_qoq_pct,
    CASE WHEN year_ago_gross_loans IS NOT NULL AND ABS(year_ago_gross_loans) > 0 AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * (gross_loans_leases - year_ago_gross_loans) / ABS(year_ago_gross_loans) END AS total_loan_growth_yoy_pct,
    CASE WHEN year_ago_equity IS NOT NULL AND ABS(year_ago_equity) > 0 AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * (equity - year_ago_equity) / ABS(year_ago_equity) END AS equity_growth_yoy_pct,
    CASE WHEN year_ago_gross_loans IS NOT NULL AND ABS(year_ago_gross_loans) > 0
              AND year_ago_deposits IS NOT NULL AND ABS(year_ago_deposits) > 0
              AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * (gross_loans_leases - year_ago_gross_loans) / ABS(year_ago_gross_loans)
              - 100.0 * (deposits - year_ago_deposits) / ABS(year_ago_deposits) END AS loan_growth_minus_deposit_growth,
    CASE WHEN year_ago_asset IS NULL OR ABS(year_ago_asset) = 0 THEN NULL
         WHEN 100.0 * (asset - year_ago_asset) / ABS(year_ago_asset) > 25 THEN 1 ELSE 0 END AS rapid_asset_growth_flag,
    CASE WHEN year_ago_gross_loans IS NULL OR ABS(year_ago_gross_loans) = 0 THEN NULL
         WHEN 100.0 * (gross_loans_leases - year_ago_gross_loans) / ABS(year_ago_gross_loans) > 25 THEN 1 ELSE 0 END AS rapid_loan_growth_flag,
    CASE WHEN year_ago_gross_loans IS NULL OR ABS(year_ago_gross_loans) = 0
              OR year_ago_deposits IS NULL OR ABS(year_ago_deposits) = 0 THEN NULL
         WHEN year_ago_gross_loans IS NOT NULL AND ABS(year_ago_gross_loans) > 0
              AND year_ago_deposits IS NOT NULL AND ABS(year_ago_deposits) > 0
              AND (100.0 * (gross_loans_leases - year_ago_gross_loans) / ABS(year_ago_gross_loans)
                   - 100.0 * (deposits - year_ago_deposits) / ABS(year_ago_deposits)) > 15 THEN 1 ELSE 0 END AS funding_gap_flag
FROM staging.feature_base;
