CREATE TABLE staging.earnings_levels AS
SELECT
    cert, reporting_date,
    quarterly_return_on_assets AS return_on_assets,
    CASE WHEN equity > 0 AND prior_equity > 0 AND quarterly_net_income IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 400.0 * quarterly_net_income / ((equity + prior_equity) / 2.0) END AS return_on_equity,
    quarterly_net_interest_margin AS net_interest_margin,
    quarterly_efficiency_ratio AS efficiency_ratio,
    CASE WHEN asset > 0 AND prior_asset > 0 AND quarterly_net_income IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 400.0 * quarterly_net_income / ((asset + prior_asset) / 2.0) END AS net_income_to_average_assets,
    CASE WHEN asset > 0 AND prior_asset > 0 AND quarterly_net_interest_income IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 400.0 * quarterly_net_interest_income / ((asset + prior_asset) / 2.0) END AS net_interest_income_to_average_assets,
    CASE WHEN asset > 0 AND prior_asset > 0 AND quarterly_noninterest_expense IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 400.0 * quarterly_noninterest_expense / ((asset + prior_asset) / 2.0) END AS noninterest_expense_to_average_assets,
    CASE WHEN prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN quarterly_return_on_assets - prior_roa END AS roa_change_qoq_pp,
    CASE WHEN year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN quarterly_return_on_assets - year_ago_roa END AS roa_change_yoy_pp,
    quarterly_net_income,
    quarter_index,
    SUM(CASE WHEN quarterly_net_income IS NULL OR quarterly_net_income >= 0 THEN 1 ELSE 0 END)
        OVER (PARTITION BY cert ORDER BY reporting_date ROWS UNBOUNDED PRECEDING) AS loss_reset_group
FROM staging.feature_base;

CREATE TABLE staging.earnings_features AS
WITH loss_counts AS (
    SELECT *,
           CASE WHEN quarterly_net_income IS NULL THEN NULL
                WHEN quarterly_net_income < 0 THEN
                SUM(CASE WHEN quarterly_net_income < 0 THEN 1 ELSE 0 END)
                OVER (PARTITION BY cert, loss_reset_group ORDER BY reporting_date ROWS UNBOUNDED PRECEDING)
                ELSE 0 END AS consecutive_loss_quarters
    FROM staging.earnings_levels
)
SELECT
    *,
    CASE WHEN COUNT(return_on_assets) OVER trailing_8 = 8
         THEN AVG(return_on_assets) OVER trailing_8 END AS roa_mean_8q,
    CASE WHEN COUNT(return_on_assets) OVER trailing_8 = 8
         THEN STDDEV_SAMP(return_on_assets) OVER trailing_8 END AS roa_volatility_8q,
    CASE WHEN roa_change_qoq_pp IS NULL AND roa_change_yoy_pp IS NULL AND consecutive_loss_quarters IS NULL THEN NULL
         WHEN roa_change_qoq_pp <= -0.50 OR roa_change_yoy_pp <= -1.00 OR consecutive_loss_quarters >= 2 THEN 1 ELSE 0 END AS earnings_deterioration_flag
FROM loss_counts
WINDOW trailing_8 AS (PARTITION BY cert ORDER BY reporting_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW);
