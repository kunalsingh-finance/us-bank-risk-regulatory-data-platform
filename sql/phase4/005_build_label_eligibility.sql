-- Eligibility records history, gaps, future events, competing exits and surveillance boundaries.
CREATE TABLE core.bank_quarter_label_eligibility AS
WITH histories AS (
    SELECT f.cert, f.rssdid, f.reporting_date,
           ROW_NUMBER() OVER (PARTITION BY f.cert ORDER BY f.reporting_date) AS history_observation_count,
           LAG(f.reporting_date) OVER (PARTITION BY f.cert ORDER BY f.reporting_date) AS prior_reporting_date
    FROM phase3.core.bank_quarter_risk_features f
), event_candidates AS (
    SELECT h.*,
           (SELECT MIN(x.closing_date) FROM core.validated_failure_events x
            WHERE x.cert=h.cert AND x.validation_status='VALIDATED' AND x.closing_date > h.reporting_date) AS next_failure_date,
           (SELECT MIN(x.closing_date) FROM core.validated_failure_events x
            WHERE x.cert=h.cert AND x.validation_status='VALIDATED' AND x.closing_date <= h.reporting_date) AS prior_or_same_failure_date,
           (SELECT MIN(x.event_date) FROM core.validated_nonfailure_exits x
            WHERE x.cert=h.cert AND x.validation_status='VALIDATED' AND x.event_date > h.reporting_date) AS competing_exit_date,
           (SELECT ARG_MIN(x.event_type, x.event_date) FROM core.validated_nonfailure_exits x
            WHERE x.cert=h.cert AND x.validation_status='VALIDATED' AND x.event_date > h.reporting_date) AS competing_exit_type,
           (SELECT MIN(x.assistance_event_date) FROM core.validated_assistance_events x
            WHERE x.cert=h.cert AND x.assistance_event_date > h.reporting_date) AS next_assistance_date
    FROM histories h
)
SELECT e.cert, e.rssdid, e.reporting_date, p.asset_size_band,
       COALESCE(NULLIF(f.bank_class,''), 'UNKNOWN') AS bank_class,
       e.history_observation_count, e.prior_reporting_date,
       CASE WHEN e.prior_reporting_date IS NULL THEN FALSE
            ELSE e.prior_reporting_date <> LAST_DAY(e.reporting_date - INTERVAL 3 MONTH) END AS panel_gap_flag,
       CAST(e.reporting_date + INTERVAL 12 MONTH AS DATE) AS horizon_end_4q,
       CAST(e.reporting_date + INTERVAL 24 MONTH AS DATE) AS horizon_end_8q,
       e.next_failure_date, e.prior_or_same_failure_date,
       e.competing_exit_date, e.competing_exit_type, e.next_assistance_date,
       e.history_observation_count < {{minimum_history_observations}} AS insufficient_history,
       COALESCE(q.suspected_unit_issue, FALSE) AS blocking_data_quality,
       CAST(e.reporting_date + INTERVAL 12 MONTH AS DATE) <= DATE '{{surveillance_end_date}}' AS complete_followup_4q,
       CAST(e.reporting_date + INTERVAL 24 MONTH AS DATE) <= DATE '{{surveillance_end_date}}' AS complete_followup_8q,
       '{{label_configuration_hash}}' AS label_configuration_hash,
       '{{label_build_run_id}}' AS label_build_run_id
FROM event_candidates e
JOIN phase2.core.bank_quarter_financials f USING (cert, rssdid, reporting_date)
JOIN phase3.core.bank_peer_groups p USING (cert, rssdid, reporting_date)
JOIN phase3.core.bank_quarter_feature_quality q USING (cert, rssdid, reporting_date)
ORDER BY e.cert, e.reporting_date;
