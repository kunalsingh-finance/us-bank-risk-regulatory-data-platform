-- The institution file is current-state oriented; retain every source column.
CREATE TABLE staging.institutions AS
SELECT
    *,
    TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) AS cert_parsed,
    TRY_CAST(NULLIF(TRIM(FED_RSSD), '') AS BIGINT) AS rssdid_parsed,
    TRY_STRPTIME(NULLIF(TRIM(ESTYMD), ''), '%m/%d/%Y')::DATE AS established_date_parsed,
    CASE
        WHEN NULLIF(TRIM(ENDEFYMD), '') IS NULL OR ENDEFYMD = '12/31/9999' THEN NULL
        ELSE TRY_STRPTIME(ENDEFYMD, '%m/%d/%Y')::DATE
    END AS inactive_date_parsed,
    TRY_STRPTIME(NULLIF(TRIM(RISDATE), ''), '%m/%d/%Y')::DATE AS source_record_date_parsed,
    CASE
        WHEN TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) IS NULL THEN 'INVALID_CERT'
        WHEN NULLIF(TRIM(FED_RSSD), '') IS NOT NULL
             AND TRY_CAST(FED_RSSD AS BIGINT) IS NULL THEN 'INVALID_RSSDID'
        ELSE 'PASS'
    END AS identifier_parse_status,
    COALESCE(NULLIF(TRIM(CERT), ''), CONCAT('ROW:', ROW_NUMBER() OVER ())) AS source_record_reference,
    '{{institution_source_path}}' AS source_file,
    '{{build_run_id}}' AS ingestion_run_id
FROM read_csv(
    '{{institutions_path}}',
    header = true,
    all_varchar = true,
    strict_mode = true
);
