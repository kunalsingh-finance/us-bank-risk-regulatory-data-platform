-- Combine category outputs into the canonical feature row. All temporal calculations are backward-looking.
CREATE TABLE core.bank_quarter_risk_features AS
SELECT
    b.cert, b.rssdid, b.reporting_date, b.institution_name,
    b.source_quarter, b.source_run_id, b.source_configuration_hash, b.source_raw_hash,
    b.validation_status, b.source_file, b.source_sha256,
    '{{feature_build_run_id}}' AS feature_build_run_id,
    '{{risk_configuration_hash}}' AS feature_configuration_hash,
    '{{build_timestamp}}'::TIMESTAMP AS feature_build_timestamp,
    c.* EXCLUDE (cert, reporting_date, quarter_index),
    a.* EXCLUDE (cert, reporting_date, quarter_index, prior_noncurrent, year_ago_noncurrent, prior_date, year_ago_date),
    e.* EXCLUDE (cert, reporting_date, quarterly_net_income, quarter_index, loss_reset_group),
    l.* EXCLUDE (cert, reporting_date, prior_liquid_ratio),
    n.* EXCLUDE (cert, reporting_date, gross_loans_leases, construction_loans, multifamily_loans, residential_loans,
                 commercial_industrial_loans, consumer_ex_credit_card, credit_card_loans, covered_balance, quarter_index,
                 year_ago_hhi, year_ago_date),
    g.* EXCLUDE (cert, reporting_date)
FROM staging.feature_base b
JOIN staging.capital_features c USING (cert, reporting_date)
JOIN staging.asset_quality_features a USING (cert, reporting_date)
JOIN staging.earnings_features e USING (cert, reporting_date)
JOIN staging.liquidity_funding_features l USING (cert, reporting_date)
JOIN staging.concentration_features n USING (cert, reporting_date)
JOIN staging.growth_features g USING (cert, reporting_date)
ORDER BY b.cert, b.reporting_date;
