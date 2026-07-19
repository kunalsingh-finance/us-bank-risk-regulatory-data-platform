-- Only exact-CERT FDIC FAILURE records enter the primary event table.
CREATE TABLE core.validated_failure_events AS
WITH histories AS (
    SELECT cert, MIN(reporting_date) AS first_financial_quarter,
           MAX(reporting_date) AS last_financial_quarter,
           COUNT(*) AS financial_observations
    FROM phase2.core.bank_quarter_financials GROUP BY cert
), last_pre_event AS (
    SELECT x.failure_record_id, f.rssdid,
           ROW_NUMBER() OVER (PARTITION BY x.failure_record_id ORDER BY f.reporting_date DESC) AS sequence
    FROM phase2.core.bank_failures_reference x
    JOIN phase2.core.bank_quarter_financials f
      ON f.cert=x.cert AND f.reporting_date < x.closing_date
    WHERE x.resolution_type='FAILURE'
)
SELECT
    x.failure_record_id, x.cert, r.rssdid, x.institution_name, x.city, x.state,
    x.closing_date,
    CAST(LAST_DAY(DATE_TRUNC('quarter', x.closing_date) + INTERVAL 2 MONTH) AS DATE) AS failure_quarter,
    x.acquiring_institution, x.fund_number, x.source_file, x.source_record_reference,
    CASE WHEN h.cert IS NOT NULL THEN 'Exact CERT match' ELSE 'Unmatched' END AS match_method,
    CASE WHEN h.cert IS NOT NULL THEN 'HIGH' ELSE 'NOT_MATCHED' END AS match_confidence,
    h.first_financial_quarter, h.last_financial_quarter,
    COALESCE((SELECT COUNT(*) FROM phase2.core.bank_quarter_financials f
              WHERE f.cert=x.cert AND f.reporting_date < x.closing_date), 0) AS number_of_pre_failure_observations,
    CASE WHEN h.cert IS NOT NULL THEN 'VALIDATED'
         WHEN x.closing_date < DATE_TRUNC('year', DATE '{{panel_start_date}}') THEN 'OUTSIDE_PANEL_COVERAGE'
         ELSE 'NO_ELIGIBLE_QUARTER_END' END AS validation_status,
    CASE WHEN h.cert IS NOT NULL THEN 'NONE'
         WHEN x.closing_date < DATE_TRUNC('year', DATE '{{panel_start_date}}') THEN 'PRE_PANEL_FAILURE'
         ELSE 'FAILURE_BEFORE_FIRST_PANEL_QUARTER_END' END AS exception_status,
    x.source_sha256, '{{label_configuration_hash}}' AS label_configuration_hash,
    '{{label_build_run_id}}' AS label_build_run_id
FROM phase2.core.bank_failures_reference x
LEFT JOIN histories h USING (cert)
LEFT JOIN last_pre_event r ON r.failure_record_id=x.failure_record_id AND r.sequence=1
WHERE x.resolution_type='FAILURE'
ORDER BY x.closing_date, x.cert;
