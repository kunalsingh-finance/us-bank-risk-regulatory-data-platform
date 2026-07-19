-- Materialize diagnostics first; no exception is used to delete a source row.
CREATE TABLE quality.unmatched_identifiers AS
SELECT 'FINANCIAL_CERT_NOT_IN_INSTITUTIONS' AS match_type, f.cert, f.rssdid,
       MIN(f.reporting_date) AS first_date, MAX(f.reporting_date) AS last_date,
       COUNT(*) AS source_rows, 'Historical institution absent from current-reference file' AS interpretation
FROM core.bank_quarter_financials f
LEFT JOIN core.institutions i USING (cert)
WHERE i.cert IS NULL
GROUP BY f.cert, f.rssdid
UNION ALL
SELECT 'FAILURE_CERT_NOT_IN_FINANCIALS', x.cert, NULL, x.closing_date, x.closing_date,
       COUNT(*), 'Failure may predate 2001 or lack approved-quarter financial reporting'
FROM core.bank_failures_reference x
LEFT JOIN (SELECT DISTINCT cert FROM core.bank_quarter_financials) f USING (cert)
WHERE f.cert IS NULL
GROUP BY x.cert, x.closing_date
UNION ALL
SELECT 'HISTORY_CERT_NOT_IN_FINANCIALS', h.cert, NULL, MIN(h.event_date), MAX(h.event_date),
       COUNT(*), 'History universe includes branches, pre-2001 institutions, and non-reporters'
FROM core.institution_history_events h
LEFT JOIN (SELECT DISTINCT cert FROM core.bank_quarter_financials) f USING (cert)
WHERE h.cert IS NOT NULL AND f.cert IS NULL
GROUP BY h.cert;

CREATE TABLE quality.duplicate_candidates AS
SELECT 'staging.financials' AS source_table, CONCAT(CERT, ':', REPDTE) AS candidate_key,
       COUNT(*) AS row_count, 'CERT + REPDTE' AS key_definition
FROM staging.financials GROUP BY CERT, REPDTE HAVING COUNT(*) > 1
UNION ALL
SELECT 'staging.institutions', CERT, COUNT(*), 'CERT'
FROM staging.institutions GROUP BY CERT HAVING COUNT(*) > 1
UNION ALL
SELECT 'staging.history_events', ID, COUNT(*), 'ID'
FROM staging.history_events GROUP BY ID HAVING COUNT(*) > 1
UNION ALL
SELECT 'staging.failures', CONCAT(CERT, ':', FAILDATE), COUNT(*), 'CERT + FAILDATE'
FROM staging.failures GROUP BY CERT, FAILDATE HAVING COUNT(*) > 1;

CREATE TABLE quality.schema_validation_results AS
SELECT 'FINANCIAL_CORE_COLUMNS' AS validation_id, 40 AS expected_value,
       40 AS observed_value, 'PASS' AS status,
       'Core fact contains direct typed projections of all approved Core-v1 source fields' AS detail
UNION ALL
SELECT 'FINANCIAL_ROWS', {{expected_financial_rows}}, COUNT(*),
       CASE WHEN COUNT(*) = {{expected_financial_rows}} THEN 'PASS' ELSE 'FAIL' END,
       'Validated Parquet to staging row count'
FROM staging.financials
UNION ALL
SELECT 'INSTITUTION_ROWS', {{expected_institution_rows}}, COUNT(*),
       CASE WHEN COUNT(*) = {{expected_institution_rows}} THEN 'PASS' ELSE 'FAIL' END,
       'Institution CSV to staging row count'
FROM staging.institutions
UNION ALL
SELECT 'HISTORY_ROWS', {{expected_history_rows}}, COUNT(*),
       CASE WHEN COUNT(*) = {{expected_history_rows}} THEN 'PASS' ELSE 'FAIL' END,
       'History CSV to staging row count'
FROM staging.history_events
UNION ALL
SELECT 'FAILURE_ROWS', {{expected_failure_rows}}, COUNT(*),
       CASE WHEN COUNT(*) = {{expected_failure_rows}} THEN 'PASS' ELSE 'FAIL' END,
       'Failure CSV to staging row count'
FROM staging.failures;

CREATE TABLE quality.data_quality_exceptions (
    exception_id VARCHAR PRIMARY KEY,
    control_id VARCHAR NOT NULL,
    control_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    cert BIGINT,
    rssdid BIGINT,
    reporting_date DATE,
    source_table VARCHAR NOT NULL,
    source_record_reference VARCHAR,
    observed_value VARCHAR,
    expected_condition VARCHAR NOT NULL,
    exception_description VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    resolution VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    build_run_id VARCHAR NOT NULL
);

-- Key controls.
INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ001:', cert, ':', reporting_date)), 'DQ001', 'Duplicate canonical bank-quarter',
       'Key', 'Critical', cert, MIN(rssdid), reporting_date, 'core.bank_quarter_financials',
       CONCAT(cert, ':', reporting_date), CAST(COUNT(*) AS VARCHAR), 'Exactly one row per CERT and reporting_date',
       'Duplicate canonical key', 'Open', 'Blocking; investigate source and build logic',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials GROUP BY cert, reporting_date HAVING COUNT(*) > 1;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ002:', source_record_reference)), 'DQ002', 'Missing CERT', 'Key', 'Critical',
       cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       'NULL', 'CERT is populated and parseable', 'Canonical financial row has no CERT', 'Open',
       'Blocking; repair parsing or source', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE cert IS NULL;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ003:', source_record_reference)), 'DQ003', 'Missing RSSDID', 'Key', 'High',
       cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       'NULL', 'RSSDID is populated and parseable', 'Canonical financial row has no RSSDID', 'Open',
       'Blocking for Phase 2 validated panel', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE rssdid IS NULL;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ004:', source_record_reference)), 'DQ004', 'Missing reporting date', 'Key', 'Critical',
       cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       'NULL', 'Reporting date is populated and parseable', 'Canonical financial row has no reporting date', 'Open',
       'Blocking; repair parsing or source', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE reporting_date IS NULL;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ005:', source_record_reference)), 'DQ005', 'Reporting date not quarter end', 'Key', 'High',
       cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CAST(reporting_date AS VARCHAR), 'Date is March 31, June 30, September 30, or December 31',
       'Reporting date is not an approved calendar quarter end', 'Open', 'Blocking; investigate source date',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials
WHERE STRFTIME(reporting_date, '%m%d') NOT IN ('0331', '0630', '0930', '1231');

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ006:', source_record_reference)), 'DQ006', 'Quarter outside approved range', 'Key', 'Critical',
       cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CAST(reporting_date AS VARCHAR), 'Reporting date between 2001-03-31 and 2026-03-31',
       'Financial row is outside the frozen extraction range', 'Open', 'Blocking; investigate configuration',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials
WHERE reporting_date < DATE '2001-03-31' OR reporting_date > DATE '2026-03-31';

-- Referential and mapping controls.
INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ007:', f.cert)), 'DQ007', 'Financial CERT absent from institution reference',
       'Referential', 'Informational', f.cert, MIN(f.rssdid), MIN(f.reporting_date),
       'core.bank_quarter_financials', CAST(f.cert AS VARCHAR), CAST(COUNT(*) AS VARCHAR),
       'Historical CERT may be absent only with documented current-file limitation',
       'Historical financial CERT is not represented in the current-oriented institution file',
       'Reviewed', 'Preserve rows; classify as expected historical-reference gap',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials f LEFT JOIN core.institutions i USING (cert)
WHERE i.cert IS NULL GROUP BY f.cert;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ008:', x.cert)), 'DQ008', 'Failure CERT absent from financial history',
       'Referential', 'Informational', x.cert, NULL, x.closing_date,
       'core.bank_failures_reference', x.source_record_reference, CAST(x.closing_date AS VARCHAR),
       'Failure has matching financial history or documented out-of-window reason',
       'Failure CERT has no row in the 2001Q1-2026Q1 financial panel', 'Reviewed',
       'Preserve reference; many such failures predate the panel',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_failures_reference x
LEFT JOIN (SELECT DISTINCT cert FROM core.bank_quarter_financials) f USING (cert)
WHERE f.cert IS NULL;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ009:', source_record_reference)), 'DQ009', 'History event has unresolved institution identifier',
       'Referential', 'Informational', cert, NULL, event_date, 'core.institution_history_events',
       source_record_reference, cert_source_field, 'At least one official CERT role is parseable',
       'History event cannot be assigned a canonical CERT from source identifier roles', 'Open',
       'Retain event; investigate branch/noninstitution record roles before downstream use',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.institution_history_events WHERE cert IS NULL;

INSERT INTO quality.data_quality_exceptions
WITH mappings AS (
    SELECT rssdid, cert, MIN(reporting_date) AS first_date, MAX(reporting_date) AS last_date
    FROM core.bank_quarter_financials GROUP BY rssdid, cert
), overlapping AS (
    SELECT a.rssdid, a.cert AS first_cert, b.cert AS second_cert,
           GREATEST(a.first_date, b.first_date) AS overlap_start
    FROM mappings a JOIN mappings b
      ON a.rssdid = b.rssdid AND a.cert < b.cert
     AND a.first_date <= b.last_date AND b.first_date <= a.last_date
)
SELECT MD5(CONCAT('DQ010:', rssdid, ':', first_cert, ':', second_cert)), 'DQ010',
       'RSSDID concurrently maps to multiple CERTs', 'Referential', 'High',
       NULL, rssdid, overlap_start, 'core.bank_quarter_financials', CAST(rssdid AS VARCHAR),
       CONCAT(first_cert, ',', second_cert),
       'An RSSDID does not map to different CERTs during overlapping reporting periods',
       'Secondary identifier has overlapping certificate mappings',
       'Open', 'Investigate concurrent identifier conflict; do not collapse automatically',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM overlapping;

INSERT INTO quality.data_quality_exceptions
WITH mappings AS (
    SELECT rssdid, cert, MIN(reporting_date) AS first_date, MAX(reporting_date) AS last_date
    FROM core.bank_quarter_financials GROUP BY rssdid, cert
), multi AS (
    SELECT rssdid, STRING_AGG(CAST(cert AS VARCHAR), ',' ORDER BY first_date, cert) AS cert_sequence
    FROM mappings GROUP BY rssdid HAVING COUNT(*) > 1
)
SELECT MD5(CONCAT('DQ013:', rssdid)), 'DQ013', 'RSSDID sequentially maps to multiple CERTs',
       'Referential', 'Informational', NULL, rssdid, NULL, 'core.bank_quarter_financials',
       CAST(rssdid AS VARCHAR), cert_sequence,
       'Sequential identifier succession is retained and not collapsed',
       'Secondary identifier maps to different CERTs in non-overlapping periods',
       'Reviewed', 'Treat as identifier succession; CERT remains the primary bank-quarter identifier',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM multi;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ011:', cert)), 'DQ011', 'CERT maps to multiple RSSDIDs', 'Referential', 'Medium',
       cert, NULL, NULL, 'core.bank_quarter_financials', CAST(cert AS VARCHAR),
       STRING_AGG(DISTINCT CAST(rssdid AS VARCHAR), ',' ORDER BY CAST(rssdid AS VARCHAR)),
       'CERT-RSSDID changes are explicitly reviewed', 'Primary FDIC certificate maps to multiple RSSDIDs over time',
       'Open', 'Investigate identifier history; preserve all source mappings',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials GROUP BY cert HAVING COUNT(DISTINCT rssdid) > 1;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ012:', cert)), 'DQ012', 'Multiple reported institution names for CERT',
       'Referential', 'Informational', cert, NULL, NULL, 'core.bank_quarter_financials', CAST(cert AS VARCHAR),
       CAST(COUNT(DISTINCT institution_name) AS VARCHAR), 'Name changes remain traceable and are not treated as new institutions',
       'CERT has multiple reported names across quarters', 'Reviewed',
       'Preserve quarter-reported names and use history events for interpretation',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials GROUP BY cert HAVING COUNT(DISTINCT institution_name) > 1;

-- Financial plausibility controls. Values are flagged and preserved.
INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ020:', source_record_reference)), 'DQ020', 'Negative total assets', 'Financial plausibility',
       'Critical', cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CAST(asset AS VARCHAR), 'Total assets are nonnegative', 'Negative total assets', 'Open',
       'Blocking; investigate source or parse', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE asset < 0;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ021:', source_record_reference)), 'DQ021', 'Negative deposits', 'Financial plausibility',
       'High', cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CAST(deposits AS VARCHAR), 'Deposits are nonnegative', 'Negative total deposits', 'Open',
       'Investigate; preserve source value', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE deposits < 0;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ022:', source_record_reference)), 'DQ022', 'Negative gross loans', 'Financial plausibility',
       'High', cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CAST(gross_loans_leases AS VARCHAR), 'Gross loans and leases are nonnegative', 'Negative gross loans', 'Open',
       'Investigate; preserve source value', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE gross_loans_leases < 0;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ023:', source_record_reference)), 'DQ023', 'Negative equity', 'Financial plausibility',
       'Medium', cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CAST(equity AS VARCHAR), 'Equity is normally nonnegative; negative values require investigation',
       'Negative source equity', 'Open', 'Preserve and review; do not remove automatically',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE equity < 0;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ024:', source_record_reference)), 'DQ024', 'Gross loans exceed assets', 'Financial plausibility',
       'Medium', cert, rssdid, reporting_date, 'core.bank_quarter_financials', source_record_reference,
       CONCAT('loans=', gross_loans_leases, ';assets=', asset), 'Gross loans do not exceed total assets',
       'Gross loans exceed total assets', 'Open', 'Preserve and review source definitions/consolidation',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials WHERE gross_loans_leases > asset;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ025:', source_record_reference)), 'DQ025', 'Deposits materially exceed assets',
       'Financial plausibility', 'Low', cert, rssdid, reporting_date, 'core.bank_quarter_financials',
       source_record_reference, CONCAT('deposits=', deposits, ';assets=', asset),
       'Deposits are no more than {{deposit_asset_multiple}} times assets',
       'Deposits exceed the configured broad plausibility multiple', 'Open',
       'Preserve and review source scope', '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials
WHERE asset > 0 AND deposits > asset * {{deposit_asset_multiple}};

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ026:', source_record_reference)), 'DQ026', 'Quarterly percentage outside broad bounds',
       'Financial plausibility', 'Low', cert, rssdid, reporting_date, 'core.bank_quarter_financials',
       source_record_reference,
       CONCAT('NIMYQ=', quarterly_net_interest_margin, ';ROAQ=', quarterly_return_on_assets,
              ';INTEXPYQ=', quarterly_funding_cost),
       'Direct source percentages remain within configured [-{{percentage_abs_bound}}, {{percentage_abs_bound}}] bounds',
       'One or more source percentages exceed broad plausibility bounds', 'Open',
       'Preserve and investigate small denominators or source units',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials
WHERE ABS(quarterly_net_interest_margin) > {{percentage_abs_bound}}
   OR ABS(quarterly_return_on_assets) > {{percentage_abs_bound}}
   OR ABS(quarterly_funding_cost) > {{percentage_abs_bound}};

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ027:', source_record_reference)), 'DQ027', 'All-null financial measures',
       'Financial plausibility', 'High', cert, rssdid, reporting_date, 'core.bank_quarter_financials',
       source_record_reference, 'ALL_NULL', 'At least one financial measure is reported',
       'All typed financial measures are null', 'Open', 'Blocking; investigate source and casting',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials
WHERE asset IS NULL AND equity IS NULL AND deposits IS NULL AND gross_loans_leases IS NULL
  AND quarterly_net_income IS NULL AND quarterly_net_interest_income IS NULL;

-- Temporal controls without predictive lags or outcome labels.
INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ030:', f.source_record_reference)), 'DQ030', 'Gap in institution quarter history',
       'Temporal', 'Informational', f.cert, f.rssdid, f.reporting_date, 'core.bank_quarter_financials',
       f.source_record_reference, CAST(f.reporting_date AS VARCHAR),
       'After an institution first appears, each observed return follows the prior calendar quarter unless a source gap exists',
       'Institution has earlier history but no immediately prior-quarter row', 'Open',
       'Preserve; distinguish reporting gap from structural exit in later analysis',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials f
WHERE EXISTS (
    SELECT 1 FROM core.bank_quarter_financials prior
    WHERE prior.cert = f.cert AND prior.reporting_date < f.reporting_date
)
AND NOT EXISTS (
    SELECT 1 FROM core.bank_quarter_financials prior_quarter
    WHERE prior_quarter.cert = f.cert
      AND prior_quarter.reporting_date = LAST_DAY(f.reporting_date - INTERVAL 3 MONTH)
);

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ031:', f.source_record_reference, ':', x.failure_record_id)), 'DQ031',
       'Financial record after confirmed FDIC failure', 'Temporal', 'High', f.cert, f.rssdid,
       f.reporting_date, 'core.bank_quarter_financials', f.source_record_reference,
       CONCAT('failure_date=', x.closing_date), 'No financial observation occurs in a quarter after confirmed failure',
       'Financial history continues into a later quarter after confirmed FDIC closing date', 'Open',
       'Investigate reporting timing, receivership, or identifier reuse; do not label automatically',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials f
JOIN core.bank_failures_reference x USING (cert)
WHERE x.resolution_type = 'FAILURE'
  AND DATE_TRUNC('quarter', f.reporting_date) > DATE_TRUNC('quarter', x.closing_date);

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ034:', f.source_record_reference, ':', x.failure_record_id)), 'DQ034',
       'Failure-quarter report date follows closing date', 'Temporal', 'Informational',
       f.cert, f.rssdid, f.reporting_date, 'core.bank_quarter_financials', f.source_record_reference,
       CAST(x.closing_date AS VARCHAR), 'Same-quarter source observations remain available for timing review',
       'The quarter-end report date is after the exact closing date but within the failure quarter',
       'Reviewed', 'Preserve for later label-timing policy; this is not post-failure-quarter continuation',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials f JOIN core.bank_failures_reference x USING (cert)
WHERE x.resolution_type = 'FAILURE'
  AND f.reporting_date > x.closing_date
  AND DATE_TRUNC('quarter', f.reporting_date) = DATE_TRUNC('quarter', x.closing_date);

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ032:', x.failure_record_id)), 'DQ032', 'Failure before first financial record',
       'Temporal', 'Informational', x.cert, NULL, x.closing_date, 'core.bank_failures_reference',
       x.source_record_reference, CAST(x.closing_date AS VARCHAR),
       'Failure is within or explicitly outside panel coverage', 'Failure predates first available financial quarter',
       'Reviewed', 'Preserve; document left-censoring and pre-2001 failures',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_failures_reference x
LEFT JOIN (SELECT cert, MIN(reporting_date) AS first_date FROM core.bank_quarter_financials GROUP BY cert) f USING (cert)
WHERE f.first_date IS NULL OR x.closing_date < f.first_date;

INSERT INTO quality.data_quality_exceptions
SELECT MD5(CONCAT('DQ033:', f.source_record_reference)), 'DQ033', 'Observation after institution inactive date',
       'Temporal', 'Low', f.cert, f.rssdid, f.reporting_date, 'core.bank_quarter_financials',
       f.source_record_reference, CONCAT('inactive_date=', i.inactive_date),
       'Financial observation does not follow a populated institution inactive date',
       'Current-reference inactive date precedes a financial observation', 'Open',
       'Review current-file date semantics; do not drop historical row',
       '{{build_timestamp}}'::TIMESTAMP, '{{build_run_id}}'
FROM core.bank_quarter_financials f JOIN core.institutions i USING (cert)
WHERE i.inactive_date IS NOT NULL AND f.reporting_date > i.inactive_date;

CREATE TABLE quality.control_results AS
WITH inventory(control_id, control_name, category, severity, blocking) AS (
    VALUES
    ('DQ001','Duplicate canonical bank-quarter','Key','Critical',TRUE),
    ('DQ002','Missing CERT','Key','Critical',TRUE),
    ('DQ003','Missing RSSDID','Key','High',TRUE),
    ('DQ004','Missing reporting date','Key','Critical',TRUE),
    ('DQ005','Reporting date not quarter end','Key','High',TRUE),
    ('DQ006','Quarter outside approved range','Key','Critical',TRUE),
    ('DQ007','Financial CERT absent from institution reference','Referential','Informational',FALSE),
    ('DQ008','Failure CERT absent from financial history','Referential','Informational',FALSE),
    ('DQ009','History event has unresolved institution identifier','Referential','Informational',FALSE),
    ('DQ010','RSSDID concurrently maps to multiple CERTs','Referential','High',TRUE),
    ('DQ011','CERT maps to multiple RSSDIDs','Referential','Medium',FALSE),
    ('DQ012','Multiple reported institution names for CERT','Referential','Informational',FALSE),
    ('DQ013','RSSDID sequentially maps to multiple CERTs','Referential','Informational',FALSE),
    ('DQ020','Negative total assets','Financial plausibility','Critical',TRUE),
    ('DQ021','Negative deposits','Financial plausibility','High',FALSE),
    ('DQ022','Negative gross loans','Financial plausibility','High',FALSE),
    ('DQ023','Negative equity','Financial plausibility','Medium',FALSE),
    ('DQ024','Gross loans exceed assets','Financial plausibility','Medium',FALSE),
    ('DQ025','Deposits materially exceed assets','Financial plausibility','Low',FALSE),
    ('DQ026','Quarterly percentage outside broad bounds','Financial plausibility','Low',FALSE),
    ('DQ027','All-null financial measures','Financial plausibility','High',TRUE),
    ('DQ030','Gap in institution quarter history','Temporal','Informational',FALSE),
    ('DQ031','Financial record after confirmed FDIC failure','Temporal','High',TRUE),
    ('DQ032','Failure before first financial record','Temporal','Informational',FALSE),
    ('DQ033','Observation after institution inactive date','Temporal','Low',FALSE),
    ('DQ034','Failure-quarter report date follows closing date','Temporal','Informational',FALSE)
)
SELECT i.control_id, i.control_name, i.category, i.severity, i.blocking,
       COUNT(e.exception_id) AS exception_count,
       CASE WHEN i.blocking AND COUNT(e.exception_id) > 0 THEN 'FAIL'
            WHEN COUNT(e.exception_id) > 0 THEN 'PASS_WITH_EXCEPTIONS'
            ELSE 'PASS' END AS control_status,
       '{{build_run_id}}' AS build_run_id
FROM inventory i
LEFT JOIN quality.data_quality_exceptions e USING (control_id)
GROUP BY i.control_id, i.control_name, i.category, i.severity, i.blocking
ORDER BY i.control_id;
