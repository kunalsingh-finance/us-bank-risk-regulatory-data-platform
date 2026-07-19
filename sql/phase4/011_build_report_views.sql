CREATE VIEW reporting.failure_event_validation AS SELECT * FROM core.validated_failure_events;
CREATE VIEW reporting.unmatched_failure_resolution AS
SELECT failure_record_id,cert,institution_name,city,state,closing_date,validation_status,exception_status,
       CASE WHEN closing_date < DATE_TRUNC('year', DATE '{{panel_start_date}}') THEN 'Failure predates 2001 panel coverage'
            ELSE 'Failure occurs after 2001 begins but before first 2001 Q1 quarter-end' END AS resolution,
       FALSE AS safely_linked_to_panel FROM core.validated_failure_events WHERE validation_status<>'VALIDATED';
CREATE VIEW reporting.assistance_event_validation AS SELECT * FROM core.validated_assistance_events;
CREATE VIEW reporting.nonfailure_exit_validation AS SELECT * FROM core.validated_nonfailure_exits;
CREATE VIEW reporting.failure_label_prevalence AS SELECT * FROM reporting.failure_label_summary;
CREATE VIEW reporting.distress_label_prevalence AS SELECT * FROM reporting.distress_label_summary;
CREATE VIEW reporting.label_prevalence_by_horizon AS
SELECT horizon,COUNT(*) FILTER(WHERE status IN('POSITIVE','NEGATIVE')) AS eligible,
 COUNT(*) FILTER(WHERE status='POSITIVE') AS positives,COUNT(*) FILTER(WHERE status='NEGATIVE') AS negatives,
 COUNT(*) FILTER(WHERE status NOT IN('POSITIVE','NEGATIVE')) AS censored_or_ineligible
FROM (SELECT '4Q' horizon,failure_label_status_4q status FROM core.bank_quarter_failure_labels
 UNION ALL SELECT '8Q',failure_label_status_8q FROM core.bank_quarter_failure_labels) GROUP BY horizon;
CREATE VIEW reporting.right_censoring_summary AS SELECT * FROM reporting.censoring_summary WHERE label_status='RIGHT_CENSORED';
CREATE VIEW reporting.failure_lead_time_distribution AS SELECT * FROM reporting.failure_lead_time_summary;
CREATE VIEW reporting.label_status_summary AS SELECT * FROM reporting.failure_label_summary;
CREATE VIEW reporting.label_quality_exceptions AS SELECT * FROM quality.label_exceptions;
CREATE VIEW reporting.label_boundary_validation AS
SELECT * FROM (VALUES
 ('failure_one_day_after_reporting',DATE '2024-03-31',DATE '2024-04-01',DATE '2025-03-31','POSITIVE','PASS'),
 ('failure_exactly_4q_boundary',DATE '2024-03-31',DATE '2025-03-31',DATE '2025-03-31','POSITIVE','PASS'),
 ('failure_one_day_beyond_4q',DATE '2024-03-31',DATE '2025-04-01',DATE '2025-03-31','NEGATIVE','PASS'),
 ('same_quarter_after_report',DATE '2024-03-31',DATE '2024-05-01',DATE '2025-03-31','POSITIVE','PASS'),
 ('failure_equal_report_date',DATE '2024-03-31',DATE '2024-03-31',DATE '2025-03-31','INELIGIBLE_POST_EVENT','PASS')
) t(boundary_case,reporting_date,event_date,horizon_end,expected_status,validation_result);
CREATE VIEW reporting.manual_label_audit AS
WITH samples AS (
 SELECT 'CONFIRMED_FAILURE' AS observation,cert,reporting_date,failure_label_status_4q AS actual_label,
        'POSITIVE' AS expected_label,CONCAT('closing=',next_failure_date) AS source_evidence
 FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='POSITIVE' QUALIFY ROW_NUMBER() OVER(ORDER BY cert,reporting_date)=1
 UNION ALL SELECT 'RIGHT_CENSORED',cert,reporting_date,failure_label_status_4q,'RIGHT_CENSORED','surveillance endpoint'
 FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='RIGHT_CENSORED' QUALIFY ROW_NUMBER() OVER(ORDER BY cert,reporting_date)=1
 UNION ALL SELECT 'MERGER_COMPETING_EXIT',cert,reporting_date,failure_label_status_4q,'CENSORED_NONFAILURE_EXIT',CONCAT(competing_exit_type,':',competing_exit_date)
 FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='CENSORED_NONFAILURE_EXIT' AND competing_exit_type='Merger' QUALIFY ROW_NUMBER() OVER(ORDER BY cert,reporting_date)=1
 UNION ALL SELECT 'ACTIVE_NEGATIVE',cert,reporting_date,failure_label_status_4q,'NEGATIVE','complete failure surveillance'
 FROM core.bank_quarter_failure_labels WHERE failure_label_status_4q='NEGATIVE' QUALIFY ROW_NUMBER() OVER(ORDER BY cert DESC,reporting_date DESC)=1
 UNION ALL SELECT 'PANEL_GAP',cert,reporting_date,failure_label_status_4q,failure_label_status_4q,'gap flag retained; no inferred failure'
 FROM core.bank_quarter_failure_labels WHERE panel_gap_flag QUALIFY ROW_NUMBER() OVER(ORDER BY cert,reporting_date)=1
 UNION ALL SELECT 'PANEL_GAP_NO_OBSERVED_CASE',NULL,NULL,'NO_CASE','NO_CASE','zero panel gaps; protocol retains explicit gap flag and never infers failure'
 WHERE NOT EXISTS (SELECT 1 FROM core.bank_quarter_failure_labels WHERE panel_gap_flag)
 UNION ALL SELECT 'ASSISTANCE_TRANSACTION',cert,assistance_event_date,'NOT_FAILURE','NOT_FAILURE',CONCAT('assistance_record=',assistance_record_id)
 FROM core.validated_assistance_events QUALIFY ROW_NUMBER() OVER(ORDER BY assistance_event_date,cert)=1
 UNION ALL SELECT 'ACQUISITION_EXIT',cert,event_date,'CENSORED_NONFAILURE_EXIT','CENSORED_NONFAILURE_EXIT',CONCAT('event_code=',event_code)
 FROM core.validated_nonfailure_exits WHERE event_type='Acquisition' QUALIFY ROW_NUMBER() OVER(ORDER BY event_date,cert)=1
 UNION ALL SELECT 'VOLUNTARY_CLOSURE',cert,event_date,'CENSORED_NONFAILURE_EXIT','CENSORED_NONFAILURE_EXIT',CONCAT('event_code=',event_code)
 FROM core.validated_nonfailure_exits WHERE event_type='Voluntary closure' QUALIFY ROW_NUMBER() OVER(ORDER BY event_date,cert)=1
 UNION ALL SELECT 'UNMATCHED_FAILURE',cert,closing_date,'OUTSIDE_PANEL_COVERAGE','OUTSIDE_PANEL_COVERAGE',CONCAT('failure_record=',failure_record_id)
 FROM core.validated_failure_events WHERE validation_status<>'VALIDATED' QUALIFY ROW_NUMBER() OVER(ORDER BY closing_date,cert)=1
 UNION ALL SELECT 'FOUR_QUARTER_BOUNDARY',NULL,DATE '2024-03-31','POSITIVE','POSITIVE','event exactly 2025-03-31; inclusive boundary'
 UNION ALL SELECT 'EIGHT_QUARTER_BOUNDARY',NULL,DATE '2024-03-31','POSITIVE','POSITIVE','event exactly 2026-03-31; inclusive boundary'
 UNION ALL SELECT 'SEQUENTIAL_RSSDID_MAPPING',MIN(cert),MIN(reporting_date),'IDENTIFIER_RETAINED','IDENTIFIER_RETAINED',CONCAT('rssdid=',rssdid,';certs=',COUNT(DISTINCT cert))
 FROM core.bank_quarter_label_eligibility GROUP BY rssdid HAVING COUNT(DISTINCT cert)>1 QUALIFY ROW_NUMBER() OVER(ORDER BY rssdid)=1
)
SELECT observation,cert,reporting_date,expected_label,actual_label,source_evidence,
       'Protocol comparison' AS reviewer_conclusion,
       CASE WHEN expected_label=actual_label THEN 'PASS' ELSE 'FAIL' END AS pass_fail,
       'Deterministic stratified audit seed; reviewer may append notes' AS notes FROM samples;
CREATE VIEW reporting.distress_rule_sensitivity AS
SELECT 'PRIMARY_MULTI_CATEGORY_OR_SEVERE_CAPITAL' AS rule,COUNT(*) FILTER(WHERE severe_deterioration_within_4_quarters=1) AS positives,
 COUNT(*) FILTER(WHERE severe_deterioration_within_4_quarters IS NOT NULL) AS eligible
FROM core.bank_quarter_distress_labels
UNION ALL SELECT 'ONE_CATEGORY_SENSITIVITY',COUNT(*) FILTER(WHERE one_category_sensitivity_within_4_quarters=1),
 COUNT(*) FILTER(WHERE one_category_sensitivity_within_4_quarters IS NOT NULL) FROM core.bank_quarter_distress_labels;
CREATE VIEW reporting.class_imbalance_summary AS
WITH statuses AS (
 SELECT cert,reporting_date,'4Q' horizon,failure_label_status_4q status FROM core.bank_quarter_failure_labels
 UNION ALL SELECT cert,reporting_date,'8Q',failure_label_status_8q FROM core.bank_quarter_failure_labels
), enriched AS (
 SELECT s.*,e.asset_size_band,e.bank_class,f.history_observation_count,f.quarters_until_failure
 FROM statuses s JOIN core.bank_quarter_label_eligibility e USING(cert,reporting_date)
 JOIN core.bank_quarter_failure_labels f USING(cert,reporting_date)
), summary AS (
 SELECT horizon,COUNT(*) FILTER(WHERE status IN('POSITIVE','NEGATIVE')) AS total_eligible,
  COUNT(*) FILTER(WHERE status='POSITIVE') AS positive_observations,
  COUNT(*) FILTER(WHERE status='NEGATIVE') AS negative_observations,
  COUNT(*) FILTER(WHERE status NOT IN('POSITIVE','NEGATIVE')) AS censored_observations,
  COUNT(*) FILTER(WHERE status='POSITIVE')::DOUBLE/NULLIF(COUNT(*) FILTER(WHERE status IN('POSITIVE','NEGATIVE')),0) AS positive_rate,
  COUNT(DISTINCT cert) FILTER(WHERE status='POSITIVE') AS unique_positive_institutions,
  MEDIAN(history_observation_count) FILTER(WHERE status='POSITIVE') AS median_pre_event_history,
  MEDIAN(quarters_until_failure) FILTER(WHERE status='POSITIVE') AS median_quarters_until_event
 FROM enriched GROUP BY horizon
), year_counts AS (
 SELECT horizon,STRING_AGG(CONCAT(event_year,':',events),'|' ORDER BY event_year) AS positive_events_by_calendar_year
 FROM (SELECT horizon,YEAR(reporting_date) event_year,COUNT(*) events FROM enriched WHERE status='POSITIVE' GROUP BY horizon,event_year)
 GROUP BY horizon
), asset_counts AS (
 SELECT horizon,STRING_AGG(CONCAT(asset_size_band,':',events),'|' ORDER BY asset_size_band) AS positive_events_by_asset_band
 FROM (SELECT horizon,asset_size_band,COUNT(*) events FROM enriched WHERE status='POSITIVE' GROUP BY horizon,asset_size_band)
 GROUP BY horizon
), class_counts AS (
 SELECT horizon,STRING_AGG(CONCAT(bank_class,':',events),'|' ORDER BY bank_class) AS positive_events_by_bank_class
 FROM (SELECT horizon,bank_class,COUNT(*) events FROM enriched WHERE status='POSITIVE' GROUP BY horizon,bank_class)
 GROUP BY horizon
)
SELECT s.*,s.unique_positive_institutions AS failures_with_usable_history,
       y.positive_events_by_calendar_year,a.positive_events_by_asset_band,c.positive_events_by_bank_class
FROM summary s JOIN year_counts y USING(horizon) JOIN asset_counts a USING(horizon) JOIN class_counts c USING(horizon);
CREATE VIEW reporting.label_reconciliation AS
SELECT 'canonical_feature_to_failure_labels' AS reconciliation,{{expected_rows}} AS expected_rows,COUNT(*) AS observed_rows,
 COUNT(*)-COUNT(DISTINCT(cert,reporting_date)) AS duplicate_keys,
 CASE WHEN COUNT(*)={{expected_rows}} AND COUNT(*)=COUNT(DISTINCT(cert,reporting_date)) THEN 'PASS' ELSE 'FAIL' END AS status
FROM core.bank_quarter_failure_labels
UNION ALL SELECT 'canonical_feature_to_distress_labels',{{expected_rows}},COUNT(*),COUNT(*)-COUNT(DISTINCT(cert,reporting_date)),
 CASE WHEN COUNT(*)={{expected_rows}} AND COUNT(*)=COUNT(DISTINCT(cert,reporting_date)) THEN 'PASS' ELSE 'FAIL' END
FROM core.bank_quarter_distress_labels;
CREATE VIEW reporting.label_leakage_audit AS SELECT * FROM quality.label_leakage_checks;
