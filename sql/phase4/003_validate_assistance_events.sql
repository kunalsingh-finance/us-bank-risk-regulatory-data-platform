-- Assistance is preserved for sensitivity analysis and never enters the primary failure label.
CREATE TABLE core.validated_assistance_events AS
SELECT
    x.failure_record_id AS assistance_record_id, x.cert,
    (SELECT f.rssdid FROM phase2.core.bank_quarter_financials f
     WHERE f.cert=x.cert AND f.reporting_date < x.closing_date
     ORDER BY f.reporting_date DESC LIMIT 1) AS rssdid,
    x.institution_name, x.city, x.state, x.closing_date AS assistance_event_date,
    CAST(LAST_DAY(DATE_TRUNC('quarter', x.closing_date) + INTERVAL 2 MONTH) AS DATE) AS assistance_event_quarter,
    x.acquiring_institution, x.fund_number, x.source_file, x.source_record_reference,
    CASE WHEN EXISTS (SELECT 1 FROM phase2.core.bank_quarter_financials f WHERE f.cert=x.cert)
         THEN 'Exact CERT match' ELSE 'Unmatched' END AS match_method,
    CASE WHEN EXISTS (SELECT 1 FROM phase2.core.bank_quarter_financials f WHERE f.cert=x.cert)
         THEN 'VALIDATED' ELSE 'UNMATCHED' END AS validation_status,
    x.source_sha256, '{{label_configuration_hash}}' AS label_configuration_hash,
    '{{label_build_run_id}}' AS label_build_run_id
FROM phase2.core.bank_failures_reference x
WHERE x.resolution_type='ASSISTANCE'
ORDER BY x.closing_date, x.cert;
