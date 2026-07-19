-- Retain the 244-column history event source and parse all identifier roles explicitly.
CREATE TABLE staging.history_events AS
SELECT
    *,
    TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) AS cert_parsed,
    TRY_CAST(NULLIF(TRIM(FRM_CERT), '') AS BIGINT) AS former_cert_parsed,
    TRY_CAST(NULLIF(TRIM(OUT_CERT), '') AS BIGINT) AS outgoing_cert_parsed,
    TRY_CAST(NULLIF(TRIM(SUR_CERT), '') AS BIGINT) AS surviving_cert_parsed,
    TRY_CAST(NULLIF(TRIM(ACQ_CERT), '') AS BIGINT) AS acquiring_cert_parsed,
    COALESCE(
        TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT),
        TRY_CAST(NULLIF(TRIM(OUT_CERT), '') AS BIGINT),
        TRY_CAST(NULLIF(TRIM(SUR_CERT), '') AS BIGINT),
        TRY_CAST(NULLIF(TRIM(ACQ_CERT), '') AS BIGINT),
        TRY_CAST(NULLIF(TRIM(FRM_CERT), '') AS BIGINT)
    ) AS canonical_cert_parsed,
    COALESCE(
        TRY_CAST(NULLIF(TRIM(EFFDATE), '') AS TIMESTAMP)::DATE,
        TRY_STRPTIME(NULLIF(TRIM(EFFDATE), ''), '%Y%m%d')::DATE
    ) AS event_date_parsed,
    CASE
        WHEN TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT) IS NOT NULL THEN 'CERT'
        WHEN TRY_CAST(NULLIF(TRIM(OUT_CERT), '') AS BIGINT) IS NOT NULL THEN 'OUT_CERT'
        WHEN TRY_CAST(NULLIF(TRIM(SUR_CERT), '') AS BIGINT) IS NOT NULL THEN 'SUR_CERT'
        WHEN TRY_CAST(NULLIF(TRIM(ACQ_CERT), '') AS BIGINT) IS NOT NULL THEN 'ACQ_CERT'
        WHEN TRY_CAST(NULLIF(TRIM(FRM_CERT), '') AS BIGINT) IS NOT NULL THEN 'FRM_CERT'
        ELSE 'UNRESOLVED'
    END AS canonical_cert_source,
    CASE
        WHEN COALESCE(
            TRY_CAST(NULLIF(TRIM(CERT), '') AS BIGINT),
            TRY_CAST(NULLIF(TRIM(OUT_CERT), '') AS BIGINT),
            TRY_CAST(NULLIF(TRIM(SUR_CERT), '') AS BIGINT),
            TRY_CAST(NULLIF(TRIM(ACQ_CERT), '') AS BIGINT),
            TRY_CAST(NULLIF(TRIM(FRM_CERT), '') AS BIGINT)
        ) IS NULL THEN 'UNRESOLVED_IDENTIFIER'
        WHEN COALESCE(
            TRY_CAST(NULLIF(TRIM(EFFDATE), '') AS TIMESTAMP)::DATE,
            TRY_STRPTIME(NULLIF(TRIM(EFFDATE), ''), '%Y%m%d')::DATE
        ) IS NULL THEN 'INVALID_EVENT_DATE'
        ELSE 'PASS'
    END AS parse_status,
    COALESCE(NULLIF(TRIM(ID), ''), CONCAT('TRANS:', TRANSNUM, ':', ROW_NUMBER() OVER ())) AS source_record_reference,
    '{{history_source_path}}' AS source_file,
    '{{build_run_id}}' AS ingestion_run_id
FROM read_csv(
    '{{history_path}}',
    header = true,
    all_varchar = true,
    strict_mode = true
);
