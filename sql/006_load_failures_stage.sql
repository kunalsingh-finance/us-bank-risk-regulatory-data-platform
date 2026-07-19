-- Failure data remain a descriptive reference and are not converted to labels.
CREATE TABLE staging.failures AS
SELECT
    *,
    TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) AS cert_parsed,
    TRY_STRPTIME(NULLIF(TRIM(FAILDATE), ''), '%m/%d/%Y')::DATE AS failure_date_parsed,
    CASE
        WHEN TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) IS NULL THEN 'INVALID_CERT'
        WHEN TRY_STRPTIME(NULLIF(TRIM(FAILDATE), ''), '%m/%d/%Y') IS NULL THEN 'INVALID_FAILURE_DATE'
        ELSE 'PASS'
    END AS parse_status,
    COALESCE(NULLIF(TRIM(ID), ''), CONCAT('CERT:', CERT, ':', FAILDATE)) AS source_record_reference,
    '{{failure_source_path}}' AS source_file,
    '{{build_run_id}}' AS ingestion_run_id
FROM read_csv(
    '{{failures_path}}',
    header = true,
    all_varchar = true,
    strict_mode = true
);
