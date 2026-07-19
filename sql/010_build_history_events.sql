-- Official source codes and flags drive a descriptive, traceable taxonomy.
CREATE TABLE core.institution_history_events AS
SELECT
    TRY_CAST(NULLIF(TRIM(ID), '') AS BIGINT) AS history_event_id,
    TRY_CAST(NULLIF(TRIM(TRANSNUM), '') AS BIGINT) AS transaction_number,
    canonical_cert_parsed AS cert,
    canonical_cert_source AS cert_source_field,
    former_cert_parsed AS former_cert,
    outgoing_cert_parsed AS outgoing_cert,
    surviving_cert_parsed AS surviving_cert,
    acquiring_cert_parsed AS acquiring_cert,
    event_date_parsed AS event_date,
    NULLIF(TRIM(CHANGECODE), '') AS event_code,
    NULLIF(TRIM(CHANGECODE_DESC), '') AS event_description,
    NULLIF(TRIM(INSTNAME), '') AS institution_name,
    NULLIF(TRIM(FRM_INSTNAME), '') AS former_institution_name,
    NULLIF(TRIM(OUT_INSTNAME), '') AS outgoing_institution_name,
    NULLIF(TRIM(SUR_INSTNAME), '') AS surviving_institution_name,
    NULLIF(TRIM(ACQ_INSTNAME), '') AS acquiring_institution_name,
    CASE
        WHEN CHANGECODE IN ('211', '215', '216', '217', '230')
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%failure%'
             OR FAILED_COM_TO_COM_FLAG = '1' OR FAILED_OTS_TO_COM_FLAG = '1'
             OR FAILED_OTS_TO_OTS_FLAG = '1' OR FAILED_OTHER_TO_COM_FLAG = '1'
             OR FAILED_RTC_FLAG = '1' THEN 'Failure-related'
        WHEN CHANGECODE = '240' OR VOLUNTARY_LIQUIDATION_FLAG = '1'
             OR WITHDRAW_INSURANCE_COM_FLAG = '1' THEN 'Voluntary closure'
        WHEN CHANGECODE IN ('223', '224', '810', '811', '812')
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%merger%'
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%consolidat%' THEN 'Merger'
        WHEN CHANGECODE IN ('221', '222', '712', '713', '722', '724')
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%acquir%'
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%purchased%'
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%sold%'
             OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%absorb%' THEN 'Acquisition'
        WHEN CHANGECODE = '510' OR LOWER(COALESCE(CHANGECODE_DESC, '')) LIKE '%legal name%' THEN 'Name change'
        WHEN CHANGECODE IN ('150', '420', '430', '440') OR NEW_CHARTER_FLAG = '1'
             OR CLASS_CHANGE_FLAG = '1' THEN 'Charter change'
        WHEN CHANGECODE = '470' OR REGAGENT_CHANGE_FLAG = '1' THEN 'Regulator change'
        WHEN NULLIF(TRIM(CHANGECODE), '') IS NULL THEN 'Unclassified'
        ELSE 'Other'
    END AS event_taxonomy,
    parse_status,
    source_record_reference,
    source_file,
    ingestion_run_id,
    '{{history_source_hash}}' AS source_sha256,
    '{{configuration_hash}}' AS build_configuration_hash,
    '010_build_history_events.sql' AS sql_version
FROM staging.history_events;
