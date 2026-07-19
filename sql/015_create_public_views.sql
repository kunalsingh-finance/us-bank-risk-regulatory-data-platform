-- Controlled reporting views; no risk scores, labels, or model features.
CREATE VIEW reporting.bank_quarter_summary AS
SELECT reporting_date, source_quarter, COUNT(*) AS institution_count,
       COUNT(DISTINCT cert) AS unique_cert_count,
       COUNT(DISTINCT rssdid) AS unique_rssdid_count,
       COUNT(*) FILTER (WHERE asset IS NULL) AS missing_asset_count,
       COUNT(*) FILTER (WHERE deposits IS NULL) AS missing_deposit_count,
       COUNT(*) FILTER (WHERE gross_loans_leases IS NULL) AS missing_loan_count
FROM core.bank_quarter_financials
GROUP BY reporting_date, source_quarter;

CREATE VIEW reporting.institution_coverage AS
SELECT f.cert, MIN(f.rssdid) AS minimum_rssdid, MAX(f.rssdid) AS maximum_rssdid,
       COUNT(DISTINCT f.rssdid) AS rssdid_count,
       MIN(f.reporting_date) AS first_reporting_date,
       MAX(f.reporting_date) AS last_reporting_date,
       COUNT(*) AS reported_quarters,
       COUNT(DISTINCT f.institution_name) AS reported_name_count,
       BOOL_OR(i.cert IS NOT NULL) AS found_in_current_institution_reference
FROM core.bank_quarter_financials f
LEFT JOIN core.institutions i USING (cert)
GROUP BY f.cert;

CREATE VIEW reporting.quarter_coverage AS
SELECT reporting_date, source_quarter, COUNT(*) AS row_count,
       COUNT(DISTINCT cert) AS unique_cert_count,
       COUNT(*) - COUNT(DISTINCT cert) AS duplicate_cert_count,
       COUNT(*) FILTER (WHERE cert IS NULL) AS missing_cert_count,
       COUNT(*) FILTER (WHERE rssdid IS NULL) AS missing_rssdid_count
FROM core.bank_quarter_financials
GROUP BY reporting_date, source_quarter;

CREATE VIEW reporting.data_quality_summary AS
SELECT severity, category, COUNT(*) AS exception_count,
       COUNT(*) FILTER (WHERE status = 'Open') AS open_count,
       COUNT(*) FILTER (WHERE status = 'Reviewed') AS reviewed_count
FROM quality.data_quality_exceptions
GROUP BY severity, category;

CREATE VIEW reporting.source_reconciliation AS
SELECT 'source_to_staging' AS reconciliation_level, source_name,
       source_rows AS input_rows, staging_rows AS output_rows, difference,
       parse_failures, validation_status
FROM reporting.source_to_staging_reconciliation
UNION ALL
SELECT 'staging_to_core', source_name, staging_rows, core_rows, difference,
       parse_failures, validation_status
FROM reporting.staging_to_core_reconciliation;
