CREATE TABLE staging.capital_levels AS
SELECT
    cert, reporting_date,
    CASE WHEN asset > 0 AND equity IS NOT NULL THEN 100.0 * equity / asset END AS equity_to_assets,
    CASE WHEN prior_equity IS NOT NULL AND ABS(prior_equity) > 0
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 100.0 * (equity - prior_equity) / ABS(prior_equity) END AS equity_change_qoq_pct,
    CASE WHEN year_ago_equity IS NOT NULL AND ABS(year_ago_equity) > 0
              AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * (equity - year_ago_equity) / ABS(year_ago_equity) END AS equity_change_yoy_pct,
    CASE WHEN asset > 0 AND equity IS NOT NULL AND prior_asset > 0 AND prior_equity IS NOT NULL
              AND prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)
         THEN 100.0 * equity / asset - 100.0 * prior_equity / prior_asset END AS equity_to_assets_change_qoq_pp,
    CASE WHEN asset > 0 AND equity IS NOT NULL AND year_ago_asset > 0 AND year_ago_equity IS NOT NULL
              AND year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
         THEN 100.0 * equity / asset - 100.0 * year_ago_equity / year_ago_asset END AS equity_to_assets_change_yoy_pp,
    quarter_index
FROM staging.feature_base;

CREATE TABLE staging.capital_features AS
SELECT
    *,
    CASE WHEN COUNT(equity_to_assets) OVER trailing_8 = 8
         THEN REGR_SLOPE(equity_to_assets, quarter_index) OVER trailing_8 END AS equity_to_assets_slope_8q,
    CASE WHEN COUNT(equity_to_assets) OVER trailing_8 = 8
         THEN STDDEV_SAMP(equity_to_assets) OVER trailing_8 END AS equity_to_assets_volatility_8q,
    CASE WHEN equity_to_assets_change_qoq_pp IS NULL AND equity_to_assets_change_yoy_pp IS NULL THEN NULL
         WHEN equity_to_assets_change_qoq_pp <= -1.0 OR equity_to_assets_change_yoy_pp <= -2.0 THEN 1 ELSE 0 END AS capital_deterioration_flag
FROM staging.capital_levels
WINDOW trailing_8 AS (PARTITION BY cert ORDER BY reporting_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW);
