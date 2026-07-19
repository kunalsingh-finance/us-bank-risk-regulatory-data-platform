CREATE VIEW reporting.failure_label_summary AS
SELECT horizon,status,COUNT(*) AS observations,
       COUNT(DISTINCT cert) AS institutions
FROM (
 SELECT cert,'4Q' AS horizon,failure_label_status_4q AS status FROM core.bank_quarter_failure_labels
 UNION ALL
 SELECT cert,'8Q',failure_label_status_8q FROM core.bank_quarter_failure_labels
) GROUP BY horizon,status;

CREATE VIEW reporting.distress_label_summary AS
SELECT distress_label_status AS status,COUNT(*) AS observations,COUNT(DISTINCT cert) AS institutions,
       SUM(COALESCE(severe_deterioration_within_4_quarters,0)) AS positives
FROM core.bank_quarter_distress_labels GROUP BY distress_label_status;

CREATE VIEW reporting.label_prevalence_by_quarter AS
SELECT reporting_date,horizon,
       COUNT(*) FILTER(WHERE status IN ('POSITIVE','NEGATIVE')) AS eligible,
       COUNT(*) FILTER(WHERE status='POSITIVE') AS positives,
       COUNT(*) FILTER(WHERE status='NEGATIVE') AS negatives,
       COUNT(*) FILTER(WHERE status NOT IN ('POSITIVE','NEGATIVE')) AS censored_or_ineligible,
       COUNT(*) FILTER(WHERE status='POSITIVE')::DOUBLE/NULLIF(COUNT(*) FILTER(WHERE status IN ('POSITIVE','NEGATIVE')),0) AS positive_rate
FROM (
 SELECT reporting_date,'4Q' AS horizon,failure_label_status_4q AS status FROM core.bank_quarter_failure_labels
 UNION ALL SELECT reporting_date,'8Q',failure_label_status_8q FROM core.bank_quarter_failure_labels
) GROUP BY reporting_date,horizon;

CREATE VIEW reporting.label_prevalence_by_asset_band AS
SELECT e.asset_size_band,x.horizon,x.status,COUNT(*) AS observations,COUNT(DISTINCT e.cert) AS institutions
FROM core.bank_quarter_label_eligibility e
JOIN (SELECT cert,reporting_date,'4Q' AS horizon,failure_label_status_4q AS status FROM core.bank_quarter_failure_labels
      UNION ALL SELECT cert,reporting_date,'8Q',failure_label_status_8q FROM core.bank_quarter_failure_labels) x
USING(cert,reporting_date) GROUP BY e.asset_size_band,x.horizon,x.status;

CREATE VIEW reporting.censoring_summary AS
SELECT e.reporting_date,x.horizon,e.asset_size_band,e.bank_class,e.competing_exit_type AS exit_type,x.status AS label_status,COUNT(*) AS observations
FROM core.bank_quarter_label_eligibility e
JOIN (SELECT cert,reporting_date,'4Q' AS horizon,failure_label_status_4q AS status FROM core.bank_quarter_failure_labels
      UNION ALL SELECT cert,reporting_date,'8Q',failure_label_status_8q FROM core.bank_quarter_failure_labels) x USING(cert,reporting_date)
WHERE x.status IN ('RIGHT_CENSORED','CENSORED_NONFAILURE_EXIT')
GROUP BY e.reporting_date,x.horizon,e.asset_size_band,e.bank_class,e.competing_exit_type,x.status;

CREATE VIEW reporting.failure_lead_time_summary AS
SELECT CASE WHEN failed_within_4_quarters=1 THEN '4Q' ELSE '8Q' END AS positive_horizon,
       quarters_until_failure,COUNT(*) AS observations,COUNT(DISTINCT cert) AS institutions,
       MIN(days_until_failure) AS min_days,MEDIAN(days_until_failure) AS median_days,MAX(days_until_failure) AS max_days
FROM core.bank_quarter_failure_labels
WHERE failed_within_4_quarters=1 OR (failed_within_4_quarters IS NULL AND failed_within_8_quarters=1)
GROUP BY positive_horizon,quarters_until_failure;

CREATE VIEW reporting.competing_risk_summary AS
SELECT horizon,competing_exit_type,COUNT(*) AS observations,COUNT(DISTINCT cert) AS institutions
FROM (SELECT cert,'4Q' AS horizon,competing_exit_type FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='CENSORED_NONFAILURE_EXIT'
      UNION ALL SELECT cert,'8Q',competing_exit_type FROM core.bank_quarter_failure_labels WHERE failure_label_status_8q='CENSORED_NONFAILURE_EXIT')
GROUP BY horizon,competing_exit_type;

CREATE VIEW reporting.label_quality_summary AS
SELECT 'control' AS record_type,control_id AS item,status,observed_value AS count FROM audit.label_control_results
UNION ALL SELECT 'exception',exception_type,severity,COUNT(*) FROM quality.label_exceptions GROUP BY exception_type,severity;
