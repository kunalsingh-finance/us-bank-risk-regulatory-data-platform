-- Long-form non-null feature values make feature-specific peer counts and statistics explicit.
CREATE TABLE staging.peer_feature_values AS
SELECT cert, rssdid, reporting_date, feature_name, feature_value
FROM core.bank_quarter_risk_features
UNPIVOT (feature_value FOR feature_name IN (
    equity_to_assets, equity_change_yoy_pct,
    past_due_30_89_to_total_loans, past_due_90_plus_to_total_loans,
    nonaccrual_assets_to_total_loans, noncurrent_assets_to_total_loans,
    net_chargeoffs_to_average_loans, return_on_assets, return_on_equity,
    net_interest_margin, efficiency_ratio, roa_mean_8q, roa_volatility_8q,
    liquid_assets_to_total_assets, loans_to_deposits, deposits_to_total_assets,
    fhlb_advances_to_total_assets, deposit_growth_yoy_pct, estimated_deposit_outflow_pct,
    funding_cost, construction_to_total_loans, multifamily_to_total_loans,
    largest_reported_loan_category_share, loan_concentration_hhi,
    total_asset_growth_yoy_pct, total_loan_growth_yoy_pct, loan_growth_minus_deposit_growth
));

CREATE TABLE staging.peer_feature_grouped AS
WITH candidate_counts AS (
    SELECT v.*, g.asset_size_band, g.detailed_peer_group_id, g.broad_peer_group_id,
           COUNT(*) OVER (
               PARTITION BY v.reporting_date, g.detailed_peer_group_id, v.feature_name
           ) AS detailed_feature_peer_count
    FROM staging.peer_feature_values v
    JOIN core.bank_peer_groups g USING (cert, reporting_date)
)
SELECT *,
       CASE WHEN detailed_feature_peer_count >= 20 THEN detailed_peer_group_id ELSE broad_peer_group_id END AS final_peer_group_id,
       CASE WHEN detailed_feature_peer_count >= 20 THEN 'DETAILED_FEATURE' ELSE 'BROAD_FEATURE_FALLBACK' END AS peer_group_method
FROM candidate_counts;

CREATE TABLE staging.peer_feature_statistics AS
SELECT reporting_date, final_peer_group_id, feature_name,
       COUNT(*) AS peer_count,
       AVG(feature_value) AS peer_mean,
       MEDIAN(feature_value) AS peer_median,
       QUANTILE_CONT(feature_value, 0.25) AS peer_p25,
       QUANTILE_CONT(feature_value, 0.75) AS peer_p75
FROM staging.peer_feature_grouped
GROUP BY reporting_date, final_peer_group_id, feature_name;

CREATE TABLE staging.peer_feature_mad AS
SELECT v.reporting_date, v.final_peer_group_id, v.feature_name,
       MEDIAN(ABS(v.feature_value - s.peer_median)) AS peer_mad
FROM staging.peer_feature_grouped v
JOIN staging.peer_feature_statistics s USING (reporting_date, final_peer_group_id, feature_name)
GROUP BY v.reporting_date, v.final_peer_group_id, v.feature_name;

CREATE TABLE core.bank_quarter_peer_benchmarks AS
WITH ranked AS (
    SELECT v.*,
           PERCENT_RANK() OVER (
               PARTITION BY v.reporting_date, v.final_peer_group_id, v.feature_name
               ORDER BY v.feature_value
           ) AS bank_percentile
    FROM staging.peer_feature_grouped v
)
SELECT
    r.cert, r.rssdid, r.reporting_date, r.final_peer_group_id, r.peer_group_method,
    r.feature_name, r.feature_value, s.peer_count, s.peer_mean, s.peer_median,
    s.peer_p25, s.peer_p75, r.bank_percentile,
    CASE
        WHEN r.feature_name IN ('equity_to_assets','equity_change_yoy_pct','return_on_assets','return_on_equity',
                                'net_interest_margin','roa_mean_8q','liquid_assets_to_total_assets','deposits_to_total_assets')
        THEN 1.0 - r.bank_percentile
        WHEN r.feature_name IN ('past_due_30_89_to_total_loans','past_due_90_plus_to_total_loans',
             'nonaccrual_assets_to_total_loans','noncurrent_assets_to_total_loans','net_chargeoffs_to_average_loans',
             'efficiency_ratio','roa_volatility_8q','loans_to_deposits','fhlb_advances_to_total_assets',
             'estimated_deposit_outflow_pct','funding_cost','construction_to_total_loans',
             'largest_reported_loan_category_share','loan_concentration_hhi','total_asset_growth_yoy_pct',
             'total_loan_growth_yoy_pct','loan_growth_minus_deposit_growth')
        THEN r.bank_percentile
        ELSE NULL
    END AS risk_direction_adjusted_percentile,
    r.feature_value - s.peer_median AS difference_from_peer_median,
    CASE WHEN m.peer_mad > 0 THEN (r.feature_value - s.peer_median) / (1.4826 * m.peer_mad) END AS robust_z_score,
    m.peer_mad,
    s.peer_count < 20 AS peer_feature_count_too_small,
    '{{feature_build_run_id}}' AS feature_build_run_id,
    '{{peer_configuration_hash}}' AS peer_configuration_hash
FROM ranked r
JOIN staging.peer_feature_statistics s USING (reporting_date, final_peer_group_id, feature_name)
JOIN staging.peer_feature_mad m USING (reporting_date, final_peer_group_id, feature_name)
ORDER BY r.cert, r.reporting_date, r.feature_name;
