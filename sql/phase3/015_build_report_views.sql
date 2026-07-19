CREATE VIEW reporting.peer_group_size_summary AS
SELECT reporting_date, asset_size_band, peer_group_method,
       COUNT(*) AS bank_rows,
       COUNT(DISTINCT final_peer_group_id) AS final_groups,
       MIN(final_peer_group_size) AS minimum_group_size,
       MEDIAN(final_peer_group_size) AS median_group_size,
       MAX(final_peer_group_size) AS maximum_group_size
FROM core.bank_peer_groups
GROUP BY reporting_date, asset_size_band, peer_group_method;

CREATE VIEW reporting.risk_feature_reconciliation AS
SELECT source_rows, staged_rows, feature_rows, quality_rows, peer_group_rows,
       feature_rows - source_rows AS feature_difference,
       quality_rows - source_rows AS quality_difference,
       peer_group_rows - source_rows AS peer_group_difference,
       CASE WHEN source_rows = staged_rows AND source_rows = feature_rows
                  AND source_rows = quality_rows AND source_rows = peer_group_rows
            THEN 'PASS' ELSE 'FAIL' END AS validation_status,
       input_database_sha256, feature_build_run_id
FROM audit.feature_source_reconciliation;

CREATE VIEW reporting.feature_temporal_validation AS
SELECT
    COUNT(*) AS source_rows,
    COUNT(*) FILTER (WHERE prior_reporting_date IS NOT NULL) AS rows_with_prior,
    COUNT(*) FILTER (WHERE year_ago_reporting_date IS NOT NULL) AS rows_with_year_ago,
    COUNT(*) FILTER (WHERE prior_reporting_date >= reporting_date) AS future_prior_dates,
    COUNT(*) FILTER (WHERE year_ago_reporting_date >= reporting_date) AS future_year_ago_dates,
    COUNT(*) FILTER (WHERE prior_reporting_date = LAST_DAY(reporting_date - INTERVAL 3 MONTH)) AS exact_qoq_dates,
    COUNT(*) FILTER (WHERE year_ago_reporting_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)) AS exact_yoy_dates
FROM staging.feature_base;
