CREATE TABLE quality.feature_control_results AS
WITH controls(control_id, control_name, expected_value, observed_value, blocking) AS (
    VALUES
    ('FQ001','Feature row reconciliation',698804,(SELECT COUNT(*) FROM core.bank_quarter_risk_features),TRUE),
    ('FQ002','Feature key uniqueness',698804,(SELECT COUNT(DISTINCT (cert, reporting_date)) FROM core.bank_quarter_risk_features),TRUE),
    ('FQ003','Feature quality row reconciliation',698804,(SELECT COUNT(*) FROM core.bank_quarter_feature_quality),TRUE),
    ('FQ004','Peer group row reconciliation',698804,(SELECT COUNT(*) FROM core.bank_peer_groups),TRUE),
    ('FQ005','Missing feature CERT',0,(SELECT COUNT(*) FROM core.bank_quarter_risk_features WHERE cert IS NULL),TRUE),
    ('FQ006','Future or invalid one-quarter lag',0,(SELECT COUNT(*) FROM staging.feature_base WHERE prior_reporting_date >= reporting_date),TRUE),
    ('FQ007','Invalid percentile bounds',0,(SELECT COUNT(*) FROM core.bank_quarter_peer_benchmarks WHERE bank_percentile < 0 OR bank_percentile > 1 OR risk_direction_adjusted_percentile < 0 OR risk_direction_adjusted_percentile > 1),TRUE),
    ('FQ008','Peer quarter mismatch',0,(SELECT COUNT(*) FROM core.bank_quarter_peer_benchmarks WHERE final_peer_group_id NOT LIKE CONCAT(CAST(reporting_date AS VARCHAR), '|%')),TRUE),
    ('FQ009','Actual failure data joined into features',0,(SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='core' AND table_name='bank_quarter_risk_features' AND column_name LIKE '%fail%'),TRUE),
    ('FQ010','Infinite selected features',0,(SELECT COUNT(*) FROM core.bank_quarter_risk_features WHERE NOT ISFINITE(equity_to_assets) OR NOT ISFINITE(noncurrent_assets_to_total_loans) OR NOT ISFINITE(return_on_equity) OR NOT ISFINITE(loans_to_deposits) OR NOT ISFINITE(loan_concentration_hhi)),TRUE)
)
SELECT control_id, control_name, expected_value, observed_value, blocking,
       CASE WHEN expected_value = observed_value THEN 'PASS' ELSE 'FAIL' END AS status,
       '{{feature_build_run_id}}' AS feature_build_run_id
FROM controls ORDER BY control_id;

CREATE TABLE audit.feature_source_reconciliation AS
SELECT 698804 AS source_rows,
       (SELECT COUNT(*) FROM staging.feature_source) AS staged_rows,
       (SELECT COUNT(*) FROM core.bank_quarter_risk_features) AS feature_rows,
       (SELECT COUNT(*) FROM core.bank_quarter_feature_quality) AS quality_rows,
       (SELECT COUNT(*) FROM core.bank_peer_groups) AS peer_group_rows,
       '{{input_database_sha256}}' AS input_database_sha256,
       '{{feature_build_run_id}}' AS feature_build_run_id;
