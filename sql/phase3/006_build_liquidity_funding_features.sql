CREATE TABLE staging.liquidity_funding_levels AS
SELECT
    cert, reporting_date,
    CASE WHEN asset > 0 AND cash_balances IS NOT NULL AND securities IS NOT NULL AND fed_funds_reverse_repos IS NOT NULL
         THEN 100.0 * (cash_balances + securities + fed_funds_reverse_repos) / asset END AS liquid_assets_to_total_assets,
    CASE WHEN deposits > 0 AND gross_loans_leases IS NOT NULL THEN 100.0 * gross_loans_leases / deposits END AS loans_to_deposits,
    CASE WHEN asset > 0 AND deposits IS NOT NULL THEN 100.0 * deposits / asset END AS deposits_to_total_assets,
    CASE WHEN deposits > 0 AND assessable_deposits IS NOT NULL THEN 100.0 * assessable_deposits / deposits END AS assessable_deposits_to_total_deposits,
    CASE WHEN asset > 0 AND fhlb_advances IS NOT NULL THEN 100.0 * fhlb_advances / asset END AS fhlb_advances_to_total_assets,
    CASE WHEN prior_deposits IS NOT NULL AND ABS(prior_deposits) > 0
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 100.0 * (deposits - prior_deposits) / ABS(prior_deposits) END AS deposit_growth_qoq_pct,
    CASE WHEN year_ago_deposits IS NOT NULL AND ABS(year_ago_deposits) > 0
              AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * (deposits - year_ago_deposits) / ABS(year_ago_deposits) END AS deposit_growth_yoy_pct,
    CASE WHEN prior_deposits > 0 AND deposits IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 100.0 * GREATEST(prior_deposits - deposits, 0) / prior_deposits END AS estimated_deposit_outflow_pct,
    quarterly_funding_cost AS funding_cost,
    CASE WHEN prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN quarterly_funding_cost - prior_funding_cost END AS funding_cost_change_qoq_pp,
    CASE WHEN year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN quarterly_funding_cost - year_ago_funding_cost END AS funding_cost_change_yoy_pp,
    CASE WHEN asset > 0 AND prior_asset > 0 AND cash_balances IS NOT NULL AND securities IS NOT NULL
              AND fed_funds_reverse_repos IS NOT NULL AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN LAG(100.0 * (cash_balances + securities + fed_funds_reverse_repos) / asset)
              OVER (PARTITION BY cert ORDER BY reporting_date) END AS prior_liquid_ratio
FROM staging.feature_base;

CREATE TABLE staging.liquidity_funding_features AS
SELECT *,
       CASE WHEN prior_liquid_ratio IS NULL AND loans_to_deposits IS NULL THEN NULL
            WHEN liquid_assets_to_total_assets - prior_liquid_ratio <= -5.0 OR loans_to_deposits >= 110 THEN 1 ELSE 0 END AS liquidity_deterioration_flag,
       CASE WHEN estimated_deposit_outflow_pct IS NULL AND funding_cost_change_yoy_pp IS NULL
                  AND fhlb_advances_to_total_assets IS NULL THEN NULL
            WHEN estimated_deposit_outflow_pct >= 10 OR funding_cost_change_yoy_pp >= 1.5
                  OR fhlb_advances_to_total_assets >= 15 THEN 1 ELSE 0 END AS funding_pressure_flag
FROM staging.liquidity_funding_levels;
