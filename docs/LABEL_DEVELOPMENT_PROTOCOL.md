# Label Development Protocol

Version: `phase4-labels-v1`  
Protocol frozen before the production label build.

## Event authority and separation

The primary failure outcome uses only `core.bank_failures_reference` rows whose `resolution_type` is exactly `FAILURE`. Assistance records remain separate sensitivity events. Merger, acquisition, voluntary closure, charter conversion, and other structural exits are competing events, never failures. Names are descriptive evidence only; a final failure match requires exact CERT or a separately documented identifier crosswalk.

## Risk set and time boundaries

Each predictor observation is a canonical CERT/reporting-date row. A failure is forward-looking only when its exact FDIC closing date is strictly later than the reporting date. The four-quarter boundary is `reporting_date + 12 months`; the eight-quarter boundary is `reporting_date + 24 months`. An event on that boundary is included, while an event one day later is excluded. A closing date equal to the reporting date makes the row post-event and ineligible.

The event-source surveillance endpoint is 2026-07-15, the extraction date of the frozen FDIC failure and history sources. A confirmed negative requires the entire configured horizon to end on or before that date. Rows without full follow-up are right-censored, not zero-labelled.

## Status precedence

Every horizon receives exactly one status. Precedence is: `INELIGIBLE_POST_EVENT`, `UNRESOLVED_EVENT_MAPPING`, `INELIGIBLE_DATA_QUALITY`, `INELIGIBLE_INSUFFICIENT_HISTORY`, `POSITIVE`, `CENSORED_NONFAILURE_EXIT`, `RIGHT_CENSORED`, then `NEGATIVE`. Binary values are 1 only for positive, 0 only for negative, and null for all other statuses.

Four exact historical observations, including the predictor quarter, are required for primary modelling eligibility. Gaps are recorded; the rule does not infer failure from disappearance or re-entry. Critical/high input-quality exceptions would make a row ineligible; none are expected in the validated Phase 3 layer.

## Competing risks

The earliest validated non-failure exit strictly after the reporting date and on or before the horizon censors the observation unless a validated failure occurs first. Duplicate or failure-related history records are not allowed to create non-failure exits. Assistance remains separate and does not change the primary failure status.

## Distress outcomes

Research deterioration outcomes use only future Phase 3 features as outcome evidence. They never enter the predictor feature table. Broad Phase 3 screening flags were rejected for the primary definition after a pre-modelling prevalence check showed that a one-category rule was nearly universal and a two-screening-category rule affected roughly 31% of eligible observations. The frozen primary definition therefore uses stronger level-and-change evidence: weak/declining accounting capital; high/rising noncurrent assets; sustained losses with ROA at or below -1%; and material deposit outflow combined with elevated loans-to-deposits or FHLB reliance. A primary event requires independently severe capital (`equity_to_assets <= 2%` or year-over-year decline of at least 4 percentage points) or at least two of those independent categories. It is not a regulatory classification or official CAMELS rating.

## Leakage controls

Failure dates, closing/acquirer/fund fields, future feature values, future peer statistics, event codes, outcome-window aggregates, distress dates, and label statuses are prohibited from predictor inputs. Failure and distress evidence live only in Phase 4 event/label tables. No model result may alter this protocol.
