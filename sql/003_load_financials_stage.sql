-- Preserve the validated source text and add explicit parse controls.
CREATE TABLE staging.financials AS
SELECT
    *,
    TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) AS cert_parsed,
    TRY_CAST(NULLIF(TRIM(RSSDID), '') AS BIGINT) AS rssdid_parsed,
    TRY_STRPTIME(NULLIF(TRIM(REPDTE), ''), '%Y%m%d')::DATE AS reporting_date_parsed,
    CASE
        WHEN TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) IS NULL THEN 'INVALID_CERT'
        WHEN TRY_CAST(NULLIF(TRIM(RSSDID), '') AS BIGINT) IS NULL THEN 'INVALID_RSSDID'
        WHEN TRY_STRPTIME(NULLIF(TRIM(REPDTE), ''), '%Y%m%d') IS NULL THEN 'INVALID_REPORTING_DATE'
        ELSE 'PASS'
    END AS identifier_parse_status,
    CONCAT(CERT, ':', REPDTE) AS source_record_reference
FROM read_parquet('{{financials_path}}');
