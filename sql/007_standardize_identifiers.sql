-- Cross-source identifier inventory; no identifier is replaced by institution name.
CREATE TABLE staging.identifier_crosswalk AS
SELECT 'financials' AS source_table, cert_parsed AS cert, rssdid_parsed AS rssdid,
       NAMEFULL AS institution_name, source_record_reference
FROM staging.financials
UNION ALL
SELECT 'institutions', cert_parsed, rssdid_parsed, NAME, source_record_reference
FROM staging.institutions
UNION ALL
SELECT 'history_events', canonical_cert_parsed, NULL, INSTNAME, source_record_reference
FROM staging.history_events
UNION ALL
SELECT 'failures', cert_parsed, NULL, NAME, source_record_reference
FROM staging.failures;
