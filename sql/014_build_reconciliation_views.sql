-- Exact source/staging/core and cross-source reconciliation views.
CREATE VIEW reporting.source_to_staging_reconciliation AS
SELECT 'financials' AS source_name, {{expected_financial_rows}}::BIGINT AS source_rows,
       COUNT(*) AS staging_rows, COUNT(*) - {{expected_financial_rows}} AS difference,
       COUNT(*) FILTER (WHERE identifier_parse_status <> 'PASS') AS parse_failures,
       CASE WHEN COUNT(*) = {{expected_financial_rows}}
                 AND COUNT(*) FILTER (WHERE identifier_parse_status <> 'PASS') = 0
            THEN 'PASS' ELSE 'FAIL' END AS validation_status
FROM staging.financials
UNION ALL
SELECT 'institutions', {{expected_institution_rows}}, COUNT(*), COUNT(*) - {{expected_institution_rows}},
       COUNT(*) FILTER (WHERE identifier_parse_status <> 'PASS'),
       CASE WHEN COUNT(*) = {{expected_institution_rows}}
                 AND COUNT(*) FILTER (WHERE identifier_parse_status <> 'PASS') = 0
            THEN 'PASS' ELSE 'FAIL' END
FROM staging.institutions
UNION ALL
SELECT 'history_events', {{expected_history_rows}}, COUNT(*), COUNT(*) - {{expected_history_rows}},
       COUNT(*) FILTER (WHERE parse_status <> 'PASS'),
       CASE WHEN COUNT(*) = {{expected_history_rows}} THEN 'PASS_WITH_DOCUMENTED_PARSE_EXCEPTIONS' ELSE 'FAIL' END
FROM staging.history_events
UNION ALL
SELECT 'failures', {{expected_failure_rows}}, COUNT(*), COUNT(*) - {{expected_failure_rows}},
       COUNT(*) FILTER (WHERE parse_status <> 'PASS'),
       CASE WHEN COUNT(*) = {{expected_failure_rows}}
                 AND COUNT(*) FILTER (WHERE parse_status <> 'PASS') = 0
            THEN 'PASS' ELSE 'FAIL' END
FROM staging.failures;

CREATE VIEW reporting.staging_to_core_reconciliation AS
SELECT 'financials' AS source_name, COUNT(*) AS staging_rows,
       (SELECT COUNT(*) FROM core.bank_quarter_financials) AS core_rows,
       (SELECT COUNT(*) FROM core.bank_quarter_financials) - COUNT(*) AS difference,
       COUNT(*) FILTER (WHERE identifier_parse_status <> 'PASS') AS parse_failures,
       0::BIGINT AS excluded_rows,
       'No rows excluded; typed parses remain null only when source is null or invalid' AS exclusion_reason,
       CASE WHEN COUNT(*) = (SELECT COUNT(*) FROM core.bank_quarter_financials) THEN 'PASS' ELSE 'FAIL' END AS validation_status
FROM staging.financials
UNION ALL
SELECT 'institutions', COUNT(*), (SELECT COUNT(*) FROM core.institutions),
       (SELECT COUNT(*) FROM core.institutions) - COUNT(*),
       COUNT(*) FILTER (WHERE identifier_parse_status <> 'PASS'), 0,
       'No rows excluded',
       CASE WHEN COUNT(*) = (SELECT COUNT(*) FROM core.institutions) THEN 'PASS' ELSE 'FAIL' END
FROM staging.institutions
UNION ALL
SELECT 'history_events', COUNT(*), (SELECT COUNT(*) FROM core.institution_history_events),
       (SELECT COUNT(*) FROM core.institution_history_events) - COUNT(*),
       COUNT(*) FILTER (WHERE parse_status <> 'PASS'), 0,
       'No rows excluded; unresolved identifiers are retained',
       CASE WHEN COUNT(*) = (SELECT COUNT(*) FROM core.institution_history_events) THEN 'PASS' ELSE 'FAIL' END
FROM staging.history_events
UNION ALL
SELECT 'failures', COUNT(*), (SELECT COUNT(*) FROM core.bank_failures_reference),
       (SELECT COUNT(*) FROM core.bank_failures_reference) - COUNT(*),
       COUNT(*) FILTER (WHERE parse_status <> 'PASS'), 0,
       'No rows excluded',
       CASE WHEN COUNT(*) = (SELECT COUNT(*) FROM core.bank_failures_reference) THEN 'PASS' ELSE 'FAIL' END
FROM staging.failures;

CREATE VIEW reporting.identifier_crosswalk_summary AS
WITH financial AS (SELECT DISTINCT cert FROM core.bank_quarter_financials),
     institution AS (SELECT DISTINCT cert FROM core.institutions),
     history AS (SELECT DISTINCT cert FROM core.institution_history_events WHERE cert IS NOT NULL),
     failure AS (SELECT DISTINCT cert FROM core.bank_failures_reference),
     counts(metric, source_identifiers, matched_identifiers) AS (
         SELECT 'Financial CERT in institution reference',
                (SELECT COUNT(*) FROM financial),
                (SELECT COUNT(*) FROM financial INNER JOIN institution USING (cert))
         UNION ALL
         SELECT 'Financial CERT in history events',
                (SELECT COUNT(*) FROM financial),
                (SELECT COUNT(*) FROM financial INNER JOIN history USING (cert))
         UNION ALL
         SELECT 'Failure CERT in financial history',
                (SELECT COUNT(*) FROM failure),
                (SELECT COUNT(*) FROM failure INNER JOIN financial USING (cert))
         UNION ALL
         SELECT 'History CERT in financial history',
                (SELECT COUNT(*) FROM history),
                (SELECT COUNT(*) FROM history INNER JOIN financial USING (cert))
     )
SELECT metric, source_identifiers, matched_identifiers,
       source_identifiers - matched_identifiers AS unmatched_identifiers,
       100.0 * matched_identifiers / source_identifiers AS match_percentage
FROM counts;

CREATE VIEW reporting.failure_financial_history_reconciliation AS
SELECT x.failure_record_id, x.cert, x.institution_name, x.closing_date, x.resolution_type,
       MIN(f.reporting_date) AS first_financial_date,
       MAX(f.reporting_date) AS last_financial_date,
       COUNT(f.cert) AS financial_quarters,
       COUNT(f.cert) FILTER (
           WHERE f.reporting_date > x.closing_date
             AND DATE_TRUNC('quarter', f.reporting_date) = DATE_TRUNC('quarter', x.closing_date)
       ) AS same_failure_quarter_records,
       COUNT(f.cert) FILTER (
           WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
       ) AS later_quarter_records,
       CASE WHEN x.resolution_type <> 'FAILURE' THEN 'ASSISTANCE_REFERENCE'
            WHEN COUNT(f.cert) = 0 THEN 'NO_FINANCIAL_HISTORY'
            WHEN COUNT(f.cert) FILTER (
                WHERE DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date)
            ) > 0 THEN 'POST_FAILURE_LATER_QUARTER'
            WHEN COUNT(f.cert) FILTER (WHERE f.reporting_date > x.closing_date) > 0 THEN 'SAME_FAILURE_QUARTER_TIMING'
            ELSE 'MATCHED' END AS reconciliation_status
FROM core.bank_failures_reference x
LEFT JOIN core.bank_quarter_financials f USING (cert)
GROUP BY x.failure_record_id, x.cert, x.institution_name, x.closing_date, x.resolution_type;

CREATE VIEW reporting.history_event_reconciliation AS
SELECT event_taxonomy, COUNT(*) AS event_rows,
       COUNT(*) FILTER (WHERE cert IS NOT NULL) AS resolved_cert_rows,
       COUNT(*) FILTER (WHERE cert IS NULL) AS unresolved_cert_rows,
       COUNT(*) FILTER (WHERE event_date IS NULL) AS invalid_date_rows,
       COUNT(*) FILTER (WHERE f.cert IS NOT NULL) AS rows_with_financial_cert,
       COUNT(DISTINCT h.cert) FILTER (WHERE f.cert IS NOT NULL) AS distinct_matched_certs
FROM core.institution_history_events h
LEFT JOIN (SELECT DISTINCT cert FROM core.bank_quarter_financials) f USING (cert)
GROUP BY event_taxonomy;
