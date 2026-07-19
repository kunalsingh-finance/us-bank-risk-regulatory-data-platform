-- Binary labels are populated only for confirmed positives/negatives; all censoring stays null.
CREATE TABLE core.bank_quarter_failure_labels AS
WITH classified AS (
    SELECT e.*,
      CASE
        WHEN prior_or_same_failure_date IS NOT NULL THEN 'INELIGIBLE_POST_EVENT'
        WHEN blocking_data_quality THEN 'INELIGIBLE_DATA_QUALITY'
        WHEN insufficient_history THEN 'INELIGIBLE_INSUFFICIENT_HISTORY'
        WHEN next_failure_date > reporting_date AND next_failure_date <= horizon_end_4q
             AND (competing_exit_date IS NULL OR next_failure_date <= competing_exit_date) THEN 'POSITIVE'
        WHEN competing_exit_date > reporting_date AND competing_exit_date <= horizon_end_4q
             AND (next_failure_date IS NULL OR competing_exit_date < next_failure_date) THEN 'CENSORED_NONFAILURE_EXIT'
        WHEN NOT complete_followup_4q THEN 'RIGHT_CENSORED'
        ELSE 'NEGATIVE' END AS status_4q,
      CASE
        WHEN prior_or_same_failure_date IS NOT NULL THEN 'INELIGIBLE_POST_EVENT'
        WHEN blocking_data_quality THEN 'INELIGIBLE_DATA_QUALITY'
        WHEN insufficient_history THEN 'INELIGIBLE_INSUFFICIENT_HISTORY'
        WHEN next_failure_date > reporting_date AND next_failure_date <= horizon_end_8q
             AND (competing_exit_date IS NULL OR next_failure_date <= competing_exit_date) THEN 'POSITIVE'
        WHEN competing_exit_date > reporting_date AND competing_exit_date <= horizon_end_8q
             AND (next_failure_date IS NULL OR competing_exit_date < next_failure_date) THEN 'CENSORED_NONFAILURE_EXIT'
        WHEN NOT complete_followup_8q THEN 'RIGHT_CENSORED'
        ELSE 'NEGATIVE' END AS status_8q
    FROM core.bank_quarter_label_eligibility e
)
SELECT cert, rssdid, reporting_date,
       CASE status_4q WHEN 'POSITIVE' THEN 1 WHEN 'NEGATIVE' THEN 0 END AS failed_within_4_quarters,
       CASE status_8q WHEN 'POSITIVE' THEN 1 WHEN 'NEGATIVE' THEN 0 END AS failed_within_8_quarters,
       CASE WHEN next_failure_date > reporting_date THEN DATE_DIFF('quarter', reporting_date, next_failure_date) END AS quarters_until_failure,
       CASE WHEN next_failure_date > reporting_date THEN DATE_DIFF('day', reporting_date, next_failure_date) END AS days_until_failure,
       next_failure_date,
       CASE WHEN next_failure_date IS NOT NULL
            THEN CAST(LAST_DAY(DATE_TRUNC('quarter', next_failure_date) + INTERVAL 2 MONTH) AS DATE) END AS next_failure_quarter,
       next_failure_date IS NOT NULL AS failure_event_observed,
       status_4q AS failure_label_status_4q, status_8q AS failure_label_status_8q,
       competing_exit_date, competing_exit_type,
       status_4q='RIGHT_CENSORED' AS right_censored_4q,
       status_8q='RIGHT_CENSORED' AS right_censored_8q,
       CASE WHEN status_4q=status_8q THEN status_4q ELSE CONCAT('4q=',status_4q,';8q=',status_8q) END AS eligibility_reason,
       panel_gap_flag, history_observation_count,
       label_configuration_hash, label_build_run_id,
       'phase3.core.bank_quarter_risk_features' AS predictor_source_table,
       '{{phase3_database_sha256}}' AS predictor_source_sha256,
       '{{protocol_sha256}}' AS label_protocol_sha256,
       '{{build_timestamp}}'::TIMESTAMP AS label_build_timestamp
FROM classified ORDER BY cert, reporting_date;
