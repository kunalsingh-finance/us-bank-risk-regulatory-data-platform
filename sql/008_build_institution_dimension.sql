-- One current-reference row per FDIC certificate. No current attribute is forward-filled to history.
CREATE TABLE core.institutions AS
SELECT
    cert_parsed AS cert,
    rssdid_parsed AS rssdid,
    NULLIF(TRIM(NAME), '') AS institution_name,
    NULLIF(TRIM(CITY), '') AS city,
    NULLIF(TRIM(STALP), '') AS state,
    NULLIF(TRIM(BKCLASS), '') AS bank_class,
    NULLIF(TRIM(REGAGNT), '') AS primary_regulator,
    established_date_parsed AS established_date,
    inactive_date_parsed AS inactive_date,
    CASE WHEN ACTIVE = '1' THEN TRUE WHEN ACTIVE = '0' THEN FALSE ELSE NULL END AS active_status,
    TRY_CAST(NULLIF(TRIM(ASSET), '') AS DECIMAL(38, 6)) AS current_asset_size,
    source_record_date_parsed AS source_record_date,
    source_file,
    ingestion_run_id,
    source_record_reference,
    '{{institution_source_hash}}' AS source_sha256,
    '{{configuration_hash}}' AS build_configuration_hash,
    '008_build_institution_dimension.sql' AS sql_version
FROM staging.institutions;
