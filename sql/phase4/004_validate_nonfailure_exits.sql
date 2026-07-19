-- Institution-level structural exits are competing events, not failure substitutes.
CREATE TABLE core.validated_nonfailure_exits AS
SELECT * EXCLUDE (sequence)
FROM (
    SELECT
        x.exit_event_id, x.cert, x.exit_date AS event_date,
        CAST(LAST_DAY(DATE_TRUNC('quarter', x.exit_date) + INTERVAL 2 MONTH) AS DATE) AS event_quarter,
        CASE WHEN x.exit_classification IN ('Merger','Acquisition','Voluntary closure','Charter conversion')
             THEN x.exit_classification
             WHEN x.exit_classification='Other structural exit' THEN 'Other structural exit'
             ELSE 'Unresolved exit' END AS event_type,
        h.event_code, x.successor_cert AS successor_identifier,
        x.source_type AS evidence_source, x.source_record_reference, x.source_file, x.source_sha256,
        CASE WHEN x.cert IS NOT NULL AND x.exit_date IS NOT NULL THEN 'VALIDATED' ELSE 'UNRESOLVED' END AS validation_status,
        '{{label_configuration_hash}}' AS label_configuration_hash,
        '{{label_build_run_id}}' AS label_build_run_id,
        ROW_NUMBER() OVER (
            PARTITION BY x.cert, x.exit_date, x.exit_classification
            ORDER BY x.exit_event_id
        ) AS sequence
    FROM phase2.core.bank_exits_reference x
    LEFT JOIN phase2.core.institution_history_events h
      ON x.source_type='history_events' AND x.source_record_reference=h.source_record_reference
    WHERE x.source_type='history_events' AND x.exit_classification <> 'FDIC failure'
) WHERE sequence=1
ORDER BY cert, event_date, event_type;
