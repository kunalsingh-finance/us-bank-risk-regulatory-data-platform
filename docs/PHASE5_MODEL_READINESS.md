# Phase 5 Model Readiness

## Verdict

**Approved with restricted labels or periods.** The validated FDIC failure labels are approved for a chronological experimental protocol. Severe deterioration remains a secondary sensitivity outcome because it is threshold-defined and materially more prevalent.

1. Validated actual FDIC failures: 579 total reference events.
2. Failures matching the financial panel: 571; eight are transparently out of coverage.
3. Matched failures with usable pre-failure observations: 566 institutions contribute eligible positives.
4. Four-quarter positive observations: 2,239.
5. Eight-quarter positive observations: 4,460.
6. Unique positive banks: 566 for both primary horizons.
7. Positive rates: approximately 0.355% for 4Q and 0.754% for 8Q among confirmed eligible positives/negatives.
8. Right-censored observations: 12,736 for 4Q and 29,698 for 8Q.
9. Non-failure-exit censoring: 22,954 for 4Q and 44,730 for 8Q.
10. Assistance transactions kept separate: 13, all exact-CERT matched.
11. Approved primary outcomes: `failed_within_4_quarters` and `failed_within_8_quarters` with their status filters.
12. Sensitivity outcomes: assistance horizons and all severe-deterioration outcomes.
13. Severe deterioration has 54,067 positives among 631,947 eligible observations (about 8.6%). It is sufficiently populated for sensitivity work but remains threshold-sensitive and is not a regulatory classification.
14. No calendar year is removed from source coverage, but endpoint-censored quarters and insufficient-history rows are mandatory exclusions. Early and recent years have different failure prevalence.
15. The sample spans the 2008–2012 failure cycle and later low-event years, supporting temporal validation but creating material regime imbalance.
16. A feasible starting protocol is development through 2013, rolling/validation from 2014–2018, and a locked 2019–2024 test restricted to fully observed horizons. Exact windows must be finalized before any modelling after event-count checks; no random split is permitted.
17. Mandatory feature exclusions remain invalid denominators, insufficient history, undersized peer benchmarks, unsupported Core-v1 fields, and blocking identifier/source-quality warnings.
18. Four leakage controls pass with zero violations.
19. Phase 5 experimental-protocol work may begin. Model selection or tuning must wait until chronological windows, metrics, and decision thresholds are frozen.
