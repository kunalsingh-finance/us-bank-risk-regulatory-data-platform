CREATE VIEW reporting.risk_feature_summary AS
SELECT reporting_date, COUNT(*) AS bank_count,
       COUNT(equity_to_assets) AS equity_to_assets_available,
       COUNT(noncurrent_assets_to_total_loans) AS noncurrent_proxy_available,
       COUNT(return_on_assets) AS roa_available,
       COUNT(liquid_assets_to_total_assets) AS liquidity_proxy_available,
       COUNT(loan_concentration_hhi) AS concentration_hhi_available
FROM core.bank_quarter_risk_features
GROUP BY reporting_date ORDER BY reporting_date;

CREATE VIEW reporting.bank_feature_history AS
SELECT f.*, g.asset_size_band, g.final_peer_group_id, g.peer_group_method,
       q.denominator_exception_count, q.insufficient_lag_history,
       q.peer_group_too_small, q.extreme_preserved_value,
       q.identifier_continuity_concern, q.source_field_quality_warning,
       q.missing_numerator_count, q.conditional_field_unavailable, q.suspected_unit_issue
FROM core.bank_quarter_risk_features f
JOIN core.bank_peer_groups g USING (cert, rssdid, reporting_date)
JOIN core.bank_quarter_feature_quality q USING (cert, rssdid, reporting_date);

CREATE VIEW reporting.peer_benchmark_summary AS
SELECT reporting_date, feature_name, COUNT(*) AS benchmarked_banks,
       COUNT(DISTINCT final_peer_group_id) AS peer_groups,
       MIN(peer_count) AS minimum_peer_count, MEDIAN(peer_count) AS median_peer_count,
       COUNT(*) FILTER (WHERE peer_feature_count_too_small) AS small_feature_peer_rows
FROM core.bank_quarter_peer_benchmarks
GROUP BY reporting_date, feature_name;

CREATE VIEW reporting.feature_availability_summary AS
SELECT * FROM reporting.risk_feature_summary;

CREATE VIEW reporting.feature_quality_summary AS
SELECT quality_flag, COUNT(*) AS exception_count
FROM quality.feature_exceptions GROUP BY quality_flag ORDER BY quality_flag;
