-- Failure and exit references are descriptive only; no predictive outcome label is created.
CREATE TABLE core.bank_failures_reference AS
SELECT
    TRY_CAST(NULLIF(TRIM(ID), '') AS BIGINT) AS failure_record_id,
    cert_parsed AS cert,
    NULLIF(TRIM(NAME), '') AS institution_name,
    NULLIF(TRIM(CITY), '') AS city,
    NULLIF(TRIM(PSTALP), '') AS state,
    failure_date_parsed AS closing_date,
    NULLIF(TRIM(BIDNAME), '') AS acquiring_institution,
    TRY_CAST(NULLIF(TRIM(FUND), '') AS BIGINT) AS fund_number,
    TRY_CAST(NULLIF(TRIM(FIN), '') AS BIGINT) AS financial_institution_number,
    NULLIF(TRIM(RESTYPE), '') AS resolution_type,
    NULLIF(TRIM(RESTYPE1), '') AS resolution_type_code,
    parse_status,
    source_record_reference,
    source_file,
    ingestion_run_id,
    '{{failure_source_hash}}' AS source_sha256,
    '{{configuration_hash}}' AS build_configuration_hash,
    '011_build_failure_reference.sql' AS sql_version
FROM staging.failures;

CREATE TABLE core.bank_exits_reference AS
SELECT
    CONCAT('FAILURE:', failure_record_id) AS exit_event_id,
    cert,
    closing_date AS exit_date,
    CASE WHEN resolution_type = 'FAILURE' THEN 'FDIC failure' ELSE 'Other structural exit' END AS exit_classification,
    institution_name,
    CAST(NULL AS BIGINT) AS successor_cert,
    acquiring_institution AS successor_name,
    'failures' AS source_type,
    source_record_reference,
    source_file,
    ingestion_run_id,
    source_sha256,
    build_configuration_hash,
    '011_build_failure_reference.sql' AS sql_version
FROM core.bank_failures_reference
UNION ALL
SELECT
    CONCAT('HISTORY:', COALESCE(CAST(history_event_id AS VARCHAR), source_record_reference)),
    cert,
    event_date,
    CASE
        WHEN event_taxonomy = 'Failure-related' THEN 'FDIC failure'
        WHEN event_taxonomy = 'Merger' THEN 'Merger'
        WHEN event_taxonomy = 'Acquisition' THEN 'Acquisition'
        WHEN event_taxonomy = 'Voluntary closure' THEN 'Voluntary closure'
        WHEN event_taxonomy = 'Charter change' THEN 'Charter conversion'
        ELSE 'Other structural exit'
    END,
    COALESCE(institution_name, outgoing_institution_name),
    COALESCE(acquiring_cert, surviving_cert),
    COALESCE(acquiring_institution_name, surviving_institution_name),
    'history_events',
    source_record_reference,
    source_file,
    ingestion_run_id,
    source_sha256,
    build_configuration_hash,
    '011_build_failure_reference.sql'
FROM core.institution_history_events
WHERE event_code IN ('211', '215', '216', '217', '230', '240', '221', '222', '223', '224', '260');
