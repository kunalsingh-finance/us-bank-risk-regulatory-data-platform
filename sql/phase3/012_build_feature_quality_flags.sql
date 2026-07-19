CREATE TABLE quality.feature_denominator_exceptions (
    exception_id VARCHAR PRIMARY KEY,
    feature_name VARCHAR NOT NULL,
    cert BIGINT,
    rssdid BIGINT,
    reporting_date DATE,
    denominator_name VARCHAR NOT NULL,
    denominator_value DOUBLE,
    quality_flag VARCHAR NOT NULL,
    expected_condition VARCHAR NOT NULL,
    feature_build_run_id VARCHAR NOT NULL
);

-- One exception per denominator family avoids duplicating the same root cause across every related ratio.
INSERT INTO quality.feature_denominator_exceptions
SELECT MD5(CONCAT('ASSET:', cert, ':', reporting_date)), 'asset_denominator_family', cert, rssdid, reporting_date,
       'asset', asset,
       CASE WHEN asset IS NULL THEN 'MISSING_DENOMINATOR' WHEN asset = 0 THEN 'ZERO_DENOMINATOR' ELSE 'NEGATIVE_DENOMINATOR' END,
       'Assets must be positive and non-null', '{{feature_build_run_id}}'
FROM staging.feature_base WHERE asset IS NULL OR asset <= 0
UNION ALL
SELECT MD5(CONCAT('LOANS:', cert, ':', reporting_date)), 'loan_denominator_family', cert, rssdid, reporting_date,
       'gross_loans_leases', gross_loans_leases,
       CASE WHEN gross_loans_leases IS NULL THEN 'MISSING_DENOMINATOR' WHEN gross_loans_leases = 0 THEN 'ZERO_DENOMINATOR' ELSE 'NEGATIVE_DENOMINATOR' END,
       'Gross loans must be positive and non-null', '{{feature_build_run_id}}'
FROM staging.feature_base WHERE gross_loans_leases IS NULL OR gross_loans_leases <= 0
UNION ALL
SELECT MD5(CONCAT('DEPOSITS:', cert, ':', reporting_date)), 'deposit_denominator_family', cert, rssdid, reporting_date,
       'deposits', deposits,
       CASE WHEN deposits IS NULL THEN 'MISSING_DENOMINATOR' WHEN deposits = 0 THEN 'ZERO_DENOMINATOR' ELSE 'NEGATIVE_DENOMINATOR' END,
       'Deposits must be positive and non-null', '{{feature_build_run_id}}'
FROM staging.feature_base WHERE deposits IS NULL OR deposits <= 0
UNION ALL
SELECT MD5(CONCAT('AVG_ASSET:', cert, ':', reporting_date)), 'average_asset_denominator_family', cert, rssdid, reporting_date,
       'average_assets', CASE WHEN asset IS NOT NULL AND prior_asset IS NOT NULL THEN (asset + prior_asset) / 2.0 END,
       CASE WHEN prior_asset IS NULL THEN 'INSUFFICIENT_LAG_HISTORY'
            WHEN (asset + prior_asset) / 2.0 = 0 THEN 'ZERO_DENOMINATOR' ELSE 'NEGATIVE_DENOMINATOR' END,
       'Current and prior-quarter assets must produce a positive average', '{{feature_build_run_id}}'
FROM staging.feature_base
WHERE prior_reporting_date IS NULL OR prior_reporting_date <> LAST_DAY(reporting_date - INTERVAL 3 MONTH)
   OR asset IS NULL OR prior_asset IS NULL OR (asset + prior_asset) / 2.0 <= 0
UNION ALL
SELECT MD5(CONCAT('AVG_EQUITY:', cert, ':', reporting_date)), 'return_on_equity', cert, rssdid, reporting_date,
       'average_equity', CASE WHEN equity IS NOT NULL AND prior_equity IS NOT NULL THEN (equity + prior_equity) / 2.0 END,
       CASE WHEN prior_equity IS NULL OR equity IS NULL THEN 'MISSING_DENOMINATOR'
            WHEN (equity + prior_equity) / 2.0 = 0 THEN 'ZERO_DENOMINATOR' ELSE 'NEGATIVE_DENOMINATOR' END,
       'Current and prior-quarter equity must produce a positive average', '{{feature_build_run_id}}'
FROM staging.feature_base
WHERE prior_reporting_date IS NULL OR prior_reporting_date <> LAST_DAY(reporting_date - INTERVAL 3 MONTH)
   OR equity IS NULL OR prior_equity IS NULL OR (equity + prior_equity) / 2.0 <= 0;

CREATE TABLE quality.feature_continuity_exceptions AS
SELECT MD5(CONCAT('LAG:', cert, ':', reporting_date)) AS exception_id,
       cert, rssdid, reporting_date,
       CASE WHEN history_row_number = 1 THEN 'INSUFFICIENT_1Q_HISTORY'
            WHEN history_row_number <= 4 THEN 'INSUFFICIENT_4Q_HISTORY'
            ELSE 'IDENTIFIER_DATE_GAP' END AS quality_flag,
       '{{feature_build_run_id}}' AS feature_build_run_id
FROM staging.feature_base
WHERE prior_reporting_date IS NULL
   OR prior_reporting_date <> LAST_DAY(reporting_date - INTERVAL 3 MONTH)
   OR year_ago_reporting_date IS NULL
   OR year_ago_reporting_date <> LAST_DAY(reporting_date - INTERVAL 12 MONTH);

CREATE TABLE quality.peer_group_exceptions AS
SELECT MD5(CONCAT('PEER:', cert, ':', reporting_date)) AS exception_id,
       cert, rssdid, reporting_date, asset_size_band, detailed_peer_count, broad_peer_count,
       CASE WHEN asset_size_band = 'UNKNOWN' THEN 'UNKNOWN_ASSET_BAND'
            WHEN detailed_peer_count < 20 THEN 'DETAILED_GROUP_TOO_SMALL_FALLBACK_APPLIED'
            ELSE 'NONE' END AS quality_flag,
       '{{feature_build_run_id}}' AS feature_build_run_id
FROM core.bank_peer_groups
WHERE asset_size_band = 'UNKNOWN' OR detailed_peer_count < 20;

CREATE TABLE quality.feature_exceptions (
    exception_id VARCHAR PRIMARY KEY,
    feature_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    cert BIGINT,
    rssdid BIGINT,
    reporting_date DATE,
    numerator DOUBLE,
    denominator DOUBLE,
    observed_value DOUBLE,
    expected_condition VARCHAR NOT NULL,
    quality_flag VARCHAR NOT NULL,
    source_field VARCHAR,
    source_table VARCHAR NOT NULL,
    exception_description VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    feature_build_run_id VARCHAR NOT NULL
);

INSERT INTO quality.feature_exceptions
SELECT exception_id, feature_name, 'Denominator',
       CASE WHEN quality_flag IN ('ZERO_DENOMINATOR','NEGATIVE_DENOMINATOR') THEN 'Medium' ELSE 'Informational' END,
       cert, rssdid, reporting_date, NULL, denominator_value, NULL, expected_condition, quality_flag,
       denominator_name, 'staging.feature_base', 'Derived feature suppressed; source values preserved', 'Open',
       '{{build_timestamp}}'::TIMESTAMP, feature_build_run_id
FROM quality.feature_denominator_exceptions;

INSERT INTO quality.feature_exceptions
SELECT exception_id, 'temporal_feature_family', 'Continuity', 'Informational', cert, rssdid, reporting_date,
       NULL, NULL, NULL, 'Required prior quarter dates must exist and precede the current quarter', quality_flag,
       NULL, 'staging.feature_base', 'Lag or rolling feature remains null until sufficient history exists', 'Reviewed',
       '{{build_timestamp}}'::TIMESTAMP, feature_build_run_id
FROM quality.feature_continuity_exceptions;

INSERT INTO quality.feature_exceptions
SELECT exception_id, 'peer_group', 'Peer benchmarking', 'Informational', cert, rssdid, reporting_date,
       NULL, detailed_peer_count, broad_peer_count, 'Detailed peer group has at least 20 banks or documented fallback',
       quality_flag, 'asset, bank_class', 'core.bank_peer_groups', 'Same-quarter broad asset-band fallback retained',
       'Reviewed', '{{build_timestamp}}'::TIMESTAMP, feature_build_run_id
FROM quality.peer_group_exceptions;

INSERT INTO quality.feature_exceptions
SELECT MD5(CONCAT('EXTREME:', cert, ':', reporting_date)), 'broad_percentage_screen', 'Extreme value', 'Low',
       cert, rssdid, reporting_date, NULL, NULL,
       GREATEST(ABS(total_asset_growth_yoy_pct), ABS(total_loan_growth_yoy_pct), ABS(efficiency_ratio)),
       'Selected percentage features have absolute value at most 1000', 'EXTREME_PRESERVED_VALUE',
       NULL, 'core.bank_quarter_risk_features', 'Extreme raw feature is preserved for review', 'Open',
       '{{build_timestamp}}'::TIMESTAMP, '{{feature_build_run_id}}'
FROM core.bank_quarter_risk_features
WHERE ABS(total_asset_growth_yoy_pct) > 1000 OR ABS(total_loan_growth_yoy_pct) > 1000 OR ABS(efficiency_ratio) > 1000;

CREATE TABLE core.bank_quarter_feature_quality AS
SELECT
    f.cert, f.rssdid, f.reporting_date,
    ((s.past_due_30_89 IS NULL)::INTEGER + (s.past_due_90_plus IS NULL)::INTEGER
      + (s.nonaccrual_assets IS NULL)::INTEGER + (s.quarterly_net_income IS NULL)::INTEGER
      + (s.quarterly_net_interest_income IS NULL)::INTEGER + (s.quarterly_noninterest_expense IS NULL)::INTEGER
      + (s.cash_balances IS NULL)::INTEGER + (s.securities IS NULL)::INTEGER
      + (s.fed_funds_reverse_repos IS NULL)::INTEGER) AS missing_numerator_count,
    COUNT(d.exception_id) AS denominator_exception_count,
    COUNT(d.exception_id) FILTER (WHERE d.quality_flag = 'MISSING_DENOMINATOR') AS missing_denominator_count,
    COUNT(d.exception_id) FILTER (WHERE d.quality_flag = 'ZERO_DENOMINATOR') AS zero_denominator_count,
    COUNT(d.exception_id) FILTER (WHERE d.quality_flag = 'NEGATIVE_DENOMINATOR') AS negative_denominator_count,
    BOOL_OR(c.exception_id IS NOT NULL) AS insufficient_lag_history,
    f.equity_to_assets_slope_8q IS NULL AS insufficient_capital_rolling_history,
    f.roa_mean_8q IS NULL AS insufficient_earnings_rolling_history,
    FALSE AS conditional_field_unavailable,
    g.detailed_group_too_small AS peer_group_too_small,
    BOOL_OR(e.quality_flag = 'EXTREME_PRESERVED_VALUE') AS extreme_preserved_value,
    (f.loan_concentration_hhi < 0 OR f.loan_concentration_hhi > 1.000001
      OR f.loan_category_coverage_ratio > 150) AS suspected_unit_issue,
    EXISTS (SELECT 1 FROM phase2.quality.data_quality_exceptions q WHERE q.cert = f.cert AND q.control_id IN ('DQ011','DQ013')) AS identifier_continuity_concern,
    EXISTS (SELECT 1 FROM phase2.quality.data_quality_exceptions q WHERE q.cert = f.cert AND q.reporting_date = f.reporting_date AND q.control_id IN ('DQ023','DQ024','DQ026')) AS source_field_quality_warning,
    '{{feature_build_run_id}}' AS feature_build_run_id,
    '{{quality_configuration_hash}}' AS quality_configuration_hash
FROM core.bank_quarter_risk_features f
JOIN staging.feature_source s USING (cert, rssdid, reporting_date)
LEFT JOIN quality.feature_denominator_exceptions d USING (cert, rssdid, reporting_date)
LEFT JOIN quality.feature_continuity_exceptions c USING (cert, rssdid, reporting_date)
LEFT JOIN quality.feature_exceptions e USING (cert, rssdid, reporting_date)
JOIN core.bank_peer_groups g USING (cert, rssdid, reporting_date)
GROUP BY f.cert, f.rssdid, f.reporting_date, f.equity_to_assets_slope_8q, f.roa_mean_8q,
         g.detailed_group_too_small, s.past_due_30_89, s.past_due_90_plus, s.nonaccrual_assets,
         s.quarterly_net_income, s.quarterly_net_interest_income, s.quarterly_noninterest_expense,
         s.cash_balances, s.securities, s.fed_funds_reverse_repos,
         f.loan_concentration_hhi, f.loan_category_coverage_ratio;
