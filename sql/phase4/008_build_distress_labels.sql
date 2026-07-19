-- The future outcome window is isolated from predictor features.
CREATE TABLE core.bank_quarter_distress_labels AS
WITH future_evidence AS (
    SELECT e.cert, e.rssdid, e.reporting_date,
           MIN(d.distress_date) FILTER (WHERE d.primary_distress_event) AS first_distress_date,
           MAX(d.capital_evidence) AS capital_evidence,
           MAX(d.asset_quality_evidence) AS asset_quality_evidence,
           MAX(d.earnings_evidence) AS earnings_evidence,
           MAX(d.liquidity_funding_evidence) AS liquidity_funding_evidence,
           MAX(CAST(d.one_category_sensitivity_event AS INTEGER)) AS one_category_sensitivity
    FROM core.bank_quarter_label_eligibility e
    LEFT JOIN core.distress_events d
      ON d.cert=e.cert AND d.distress_date > e.reporting_date AND d.distress_date <= e.horizon_end_4q
    GROUP BY e.cert, e.rssdid, e.reporting_date
), classified AS (
    SELECT e.*, f.first_distress_date, f.capital_evidence, f.asset_quality_evidence,
           f.earnings_evidence, f.liquidity_funding_evidence, f.one_category_sensitivity,
           CASE
             WHEN e.prior_or_same_failure_date IS NOT NULL THEN 'INELIGIBLE_POST_EVENT'
             WHEN e.blocking_data_quality THEN 'INELIGIBLE_DATA_QUALITY'
             WHEN e.insufficient_history THEN 'INELIGIBLE_INSUFFICIENT_HISTORY'
             WHEN f.first_distress_date IS NOT NULL
                  AND (e.competing_exit_date IS NULL OR f.first_distress_date <= e.competing_exit_date) THEN 'POSITIVE'
             WHEN e.competing_exit_date > e.reporting_date AND e.competing_exit_date <= e.horizon_end_4q
                  AND (f.first_distress_date IS NULL OR e.competing_exit_date < f.first_distress_date) THEN 'CENSORED_NONFAILURE_EXIT'
             WHEN NOT e.complete_followup_4q THEN 'RIGHT_CENSORED'
             ELSE 'NEGATIVE' END AS distress_label_status
    FROM core.bank_quarter_label_eligibility e
    JOIN future_evidence f USING (cert,rssdid,reporting_date)
)
SELECT cert, rssdid, reporting_date,
       CASE distress_label_status WHEN 'POSITIVE' THEN 1 WHEN 'NEGATIVE' THEN 0 END AS severe_deterioration_within_4_quarters,
       CASE WHEN distress_label_status IN ('POSITIVE','NEGATIVE') THEN capital_evidence END AS capital_deterioration_within_4_quarters,
       CASE WHEN distress_label_status IN ('POSITIVE','NEGATIVE') THEN asset_quality_evidence END AS asset_quality_deterioration_within_4_quarters,
       CASE WHEN distress_label_status IN ('POSITIVE','NEGATIVE') THEN earnings_evidence END AS earnings_deterioration_within_4_quarters,
       CASE WHEN distress_label_status IN ('POSITIVE','NEGATIVE') THEN liquidity_funding_evidence END AS liquidity_or_funding_stress_within_4_quarters,
       CASE WHEN distress_label_status IN ('POSITIVE','NEGATIVE') THEN one_category_sensitivity END AS one_category_sensitivity_within_4_quarters,
       first_distress_date,
       CASE WHEN first_distress_date IS NOT NULL
            THEN CAST(LAST_DAY(DATE_TRUNC('quarter', first_distress_date) + INTERVAL 2 MONTH) AS DATE) END AS first_distress_quarter,
       distress_label_status, competing_exit_date, competing_exit_type,
       panel_gap_flag, history_observation_count,
       '{{distress_configuration_hash}}' AS distress_configuration_hash,
       label_configuration_hash, label_build_run_id,
       '{{protocol_sha256}}' AS label_protocol_sha256
FROM classified ORDER BY cert, reporting_date;
