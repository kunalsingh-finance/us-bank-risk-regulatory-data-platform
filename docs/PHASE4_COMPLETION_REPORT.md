# Phase 4 Completion Report

## Verdict

Phase 4 passes: **Approved with restricted labels or periods** for Phase 5 protocol development. No model, macro data, alert, dashboard, or public release was created.

## Build identity

- Branch: `phase4-labels-validation`
- Protected Phase 3 commit: `d16b710`
- Tag: `phase3-risk-features-complete`
- Label build run ID: `phase4-20260716t235000z`
- Label configuration hash: `56d51b245f4e693f6e671a90e7d81180acf0f907026fcdbbd0baacf5c86e1457`
- Distress configuration hash: `637beeaea0785c74c8165b632c237c02cda1e1e5ff7dfa347e1933a24b7ef331`
- Frozen protocol hash: `c1ac6e17359d8ee660683b2ff4348d166f5089537550d72188d3978b3d091ecf`
- Final label database hash: `ef298cc2fe13549b673f8c93d33da142b1a8bbb0c7b58cbaff4fb4095d0604b0`

## Event validation

- FDIC failures: 579; exact-CERT panel matches: 571.
- Unmatched: eight. Seven failed during 2000; one failed February 2, 2001, before the first 2001 Q1 quarter-end. None was force-linked.
- Assistance: 13 validated and kept separate.
- Validated non-failure exits: 7,581 mergers, 785 acquisitions, 465 voluntary closures, and 2,512 other structural exits retained descriptively.

## Primary failure labels

| Status | 4Q | 8Q |
|---|---:|---:|
| Positive | 2,239 | 4,460 |
| Negative | 627,970 | 587,011 |
| Right-censored | 12,736 | 29,698 |
| Censored non-failure exit | 22,954 | 44,730 |
| Insufficient history | 32,905 | 32,905 |

Both horizons sum exactly to 698,804. Binary values are populated only for positives and negatives. Competing exits are primarily mergers; assistance never enters the failure label.

## Distress outcome

The pre-modelling prevalence review rejected broad Phase 3 screening flags as too common. The frozen stronger rule yields 54,067 severe-deterioration positives among 631,947 eligible observations (about 8.6%). This remains a research sensitivity outcome, not an official regulatory classification.

## Controls and tests

- Nine SQL label controls passed.
- Four leakage controls passed with zero violations.
- Boundary cases cover same-quarter timing, exact 4Q/8Q boundaries, equal-date post-event treatment, and one-day-beyond treatment.
- The stratified manual audit covers failures, assistance, mergers, acquisitions, voluntary exits, active negatives, endpoint censoring, boundaries, identifier sequences, panel-gap policy, and unmatched events.
- Test result: 135 passed after adding 33 Phase 4 tests to all 102 earlier tests.
- Rebuild idempotency: final row counts and all 19 report hashes reproduced exactly.
- Phase 2 and Phase 3 input hashes remained unchanged.

## Artifacts and commands

Created two frozen configurations, eleven SQL files, label builder/validator/reporting modules, three production scripts plus diagnostic scripts, 19 reports, a build manifest, 33 Phase 4 tests, and eight methodology/readiness documents. Builds used `scripts/build_outcome_labels.py`; validation used `scripts/validate_outcome_labels.py` and the full unittest suite.

## Remaining risks

- Failures are rare and clustered in historical stress periods.
- Five matched failure institutions do not contribute eligible positives under the minimum-history/competing-risk policy.
- Non-failure exit evidence depends on the Phase 2 official-code subset.
- Distress prevalence is threshold-sensitive and must remain secondary.
- Locked-test feasibility depends on sparse post-2018 failure counts and must be frozen before modelling.

Phase 4 stops here.
