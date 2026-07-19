# Outcome Label Methodology

Phase 4 creates forward-looking research outcomes without changing predictor features. The primary event source is the frozen FDIC failure reference, restricted to `resolution_type='FAILURE'`. Exact CERT matching validates 571 panel failures; eight additional failures are retained as out-of-coverage events. All 13 assistance transactions remain separate.

For a quarter-end observation `t`, the four-quarter label is positive when a validated closing date is strictly after `t` and no later than `t + 12 months`. The eight-quarter label uses `t + 24 months`. End boundaries are inclusive. Events equal to `t` are post-event; observations after failure do not enter the risk set.

A negative requires complete FDIC event surveillance through the horizon and no earlier competing non-failure exit. The frozen surveillance endpoint is July 15, 2026. Incomplete endpoint follow-up is `RIGHT_CENSORED`; an earlier merger, acquisition, or voluntary closure is `CENSORED_NONFAILURE_EXIT`. Both receive null binary labels. Four prior/current observations are required for modelling eligibility. The panel contains no observed internal quarter gaps, but an explicit gap flag preserves the rule for later data refreshes.

The label table retains exact event dates, lead time, status, competing event, configuration/protocol hashes, build identity, and immutable predictor lineage. It reconciles one-for-one to 698,804 canonical bank-quarter rows.
