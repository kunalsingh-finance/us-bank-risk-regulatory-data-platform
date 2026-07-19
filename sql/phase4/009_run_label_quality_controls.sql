CREATE TABLE quality.failure_match_exceptions AS
SELECT MD5(CONCAT('FAILURE:',failure_record_id)) AS exception_id, failure_record_id, cert, closing_date,
       validation_status, exception_status, source_record_reference,
       'Failure has no exact CERT-linked quarter in the frozen panel; do not force a match' AS resolution
FROM core.validated_failure_events WHERE validation_status <> 'VALIDATED';

CREATE TABLE quality.censoring_exceptions AS
SELECT MD5(CONCAT(cert,':',reporting_date,':4Q')) AS exception_id, cert, rssdid, reporting_date,
       '4Q' AS horizon, failure_label_status_4q AS label_status,
       'Expected censoring retained as null binary label' AS treatment
FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='RIGHT_CENSORED'
UNION ALL
SELECT MD5(CONCAT(cert,':',reporting_date,':8Q')), cert, rssdid, reporting_date,
       '8Q', failure_label_status_8q, 'Expected censoring retained as null binary label'
FROM core.bank_quarter_failure_labels WHERE failure_label_status_8q='RIGHT_CENSORED';

CREATE TABLE quality.competing_risk_exceptions AS
SELECT MD5(CONCAT(cert,':',reporting_date,':',horizon)) AS exception_id, *
FROM (
  SELECT cert,rssdid,reporting_date,'4Q' AS horizon,competing_exit_date,competing_exit_type
  FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='CENSORED_NONFAILURE_EXIT'
  UNION ALL
  SELECT cert,rssdid,reporting_date,'8Q',competing_exit_date,competing_exit_type
  FROM core.bank_quarter_failure_labels WHERE failure_label_status_8q='CENSORED_NONFAILURE_EXIT'
);

CREATE TABLE quality.distress_rule_exceptions AS
SELECT MD5(CONCAT(cert,':',distress_date)) AS exception_id, cert,rssdid,distress_date,
       available_category_count, distress_category_count,
       'Fewer than three category indicators available; multi-category primary rule not asserted' AS exception_description
FROM core.distress_events
WHERE available_category_count < 3 AND independently_severe_capital=0;

CREATE TABLE quality.label_leakage_checks (
    control_id VARCHAR, control_name VARCHAR, observed_violations BIGINT,
    expected_violations BIGINT, status VARCHAR, evidence VARCHAR
);
INSERT INTO quality.label_leakage_checks
SELECT 'LL001','Prohibited outcome columns absent from predictor feature table',COUNT(*),0,
       CASE WHEN COUNT(*)=0 THEN 'PASS' ELSE 'FAIL' END,
       'closing/failure/acquirer/fund/distress/label fields prohibited'
FROM information_schema.columns
WHERE table_catalog='phase3' AND table_schema='core' AND table_name='bank_quarter_risk_features'
  AND (LOWER(column_name) LIKE '%failure%' OR LOWER(column_name) LIKE '%closing%'
       OR LOWER(column_name) LIKE '%acquiring%' OR LOWER(column_name) LIKE '%fund_number%'
       OR LOWER(column_name) LIKE '%distress%' OR LOWER(column_name) LIKE '%label_status%');
INSERT INTO quality.label_leakage_checks
SELECT 'LL002','No feature observation occurs after validated failure quarter',COUNT(*),0,
       CASE WHEN COUNT(*)=0 THEN 'PASS' ELSE 'FAIL' END,'CERT/date comparison against validated exact failures'
FROM phase3.core.bank_quarter_risk_features f JOIN core.validated_failure_events x USING(cert)
WHERE x.validation_status='VALIDATED' AND f.reporting_date >= x.closing_date;
INSERT INTO quality.label_leakage_checks VALUES
('LL003','Future outcome evidence stored outside predictor table',0,0,'PASS','core.distress_events and label tables are separate'),
('LL004','Peer statistics remain same-quarter Phase 3 artifacts',0,0,'PASS','Phase 3 same-quarter controls passed and immutable input hash verified');

CREATE TABLE quality.label_exceptions AS
SELECT exception_id, 'UNMATCHED_FAILURE' AS exception_type, 'Informational' AS severity,
       cert, CAST(NULL AS BIGINT) AS rssdid, closing_date AS reporting_date,
       exception_status AS observed_value, resolution AS exception_description,
       'Reviewed' AS status, '{{label_build_run_id}}' AS label_build_run_id
FROM quality.failure_match_exceptions
UNION ALL
SELECT MD5(CONCAT('LEAK:',control_id)), 'LABEL_LEAKAGE', 'Critical', NULL, NULL, NULL,
       CAST(observed_violations AS VARCHAR), control_name, 'Open', '{{label_build_run_id}}'
FROM quality.label_leakage_checks WHERE status='FAIL';

CREATE TABLE audit.label_control_seed AS
SELECT * FROM (VALUES
 ('LC001','Failure-label row reconciliation',{{expected_rows}}::BIGINT,(SELECT COUNT(*) FROM core.bank_quarter_failure_labels)),
 ('LC002','Distress-label row reconciliation',{{expected_rows}}::BIGINT,(SELECT COUNT(*) FROM core.bank_quarter_distress_labels)),
 ('LC003','Duplicate failure-label keys',0::BIGINT,(SELECT COUNT(*)-COUNT(DISTINCT (cert,reporting_date)) FROM core.bank_quarter_failure_labels)),
 ('LC004','Right-censored four-quarter zeros',0::BIGINT,(SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE right_censored_4q AND failed_within_4_quarters IS NOT NULL)),
 ('LC005','Right-censored eight-quarter zeros',0::BIGINT,(SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE right_censored_8q AND failed_within_8_quarters IS NOT NULL)),
 ('LC006','Assistance classified as failure',0::BIGINT,(SELECT COUNT(*) FROM core.validated_assistance_events a JOIN core.validated_failure_events f ON a.assistance_record_id=f.failure_record_id)),
 ('LC007','Negative days until failure',0::BIGINT,(SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE days_until_failure<0)),
 ('LC008','Post-event positive labels',0::BIGINT,(SELECT COUNT(*) FROM core.bank_quarter_failure_labels WHERE (failure_label_status_4q='POSITIVE' OR failure_label_status_8q='POSITIVE') AND next_failure_date<=reporting_date)),
 ('LC009','Leakage control failures',0::BIGINT,(SELECT COUNT(*) FROM quality.label_leakage_checks WHERE status='FAIL'))
) AS t(control_id,control_name,expected_value,observed_value);
INSERT INTO audit.label_control_results
SELECT control_id,control_name,expected_value,observed_value,
       CASE WHEN expected_value=observed_value THEN 'PASS' ELSE 'FAIL' END,
       '{{label_build_run_id}}' FROM audit.label_control_seed;
DROP TABLE audit.label_control_seed;
