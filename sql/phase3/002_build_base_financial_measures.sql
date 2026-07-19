-- Copy the approved Phase 2 fact without altering values; this makes the feature database self-contained.
CREATE TABLE staging.feature_source AS
SELECT * FROM phase2.core.bank_quarter_financials
ORDER BY cert, reporting_date;

CREATE TABLE staging.feature_base AS
SELECT
    s.*,
    EXTRACT(YEAR FROM reporting_date)::INTEGER * 4 + EXTRACT(QUARTER FROM reporting_date)::INTEGER AS quarter_index,
    ROW_NUMBER() OVER bank_history AS history_row_number,
    LAG(reporting_date, 1) OVER bank_history AS prior_reporting_date,
    LAG(reporting_date, 4) OVER bank_history AS year_ago_reporting_date,
    LAG(asset, 1) OVER bank_history AS prior_asset,
    LAG(asset, 4) OVER bank_history AS year_ago_asset,
    LAG(equity, 1) OVER bank_history AS prior_equity,
    LAG(equity, 4) OVER bank_history AS year_ago_equity,
    LAG(gross_loans_leases, 1) OVER bank_history AS prior_gross_loans,
    LAG(gross_loans_leases, 4) OVER bank_history AS year_ago_gross_loans,
    LAG(deposits, 1) OVER bank_history AS prior_deposits,
    LAG(deposits, 4) OVER bank_history AS year_ago_deposits,
    LAG(quarterly_return_on_assets, 1) OVER bank_history AS prior_roa,
    LAG(quarterly_return_on_assets, 4) OVER bank_history AS year_ago_roa,
    LAG(quarterly_funding_cost, 1) OVER bank_history AS prior_funding_cost,
    LAG(quarterly_funding_cost, 4) OVER bank_history AS year_ago_funding_cost
FROM staging.feature_source s
WINDOW bank_history AS (PARTITION BY cert ORDER BY reporting_date);
