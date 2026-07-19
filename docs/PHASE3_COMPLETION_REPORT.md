# Phase 3 Completion Report

## Decision

Phase 3 passes. Final verdict: **Approved with documented feature exclusions** for Phase 4 label construction.

The platform now contains 65 transparent **public-data CAMELS-style risk indicators** and quarter-specific peer benchmarks. They are not official CAMELS ratings. No labels, models, macro data, alerts, dashboard, or composite failure probability were created.

## Version control and build identity

- Branch: `phase3-risk-features`
- Protected Phase 2 commit: `a5f4c0d`
- Tag: `phase2-sql-data-model-complete`
- Feature build run ID: `phase3-20260716t230347z`
- Risk configuration hash: `72ccca9901bb8e9198b340e5b2296d5231c76cb5500d327dd87a03bb3eecc0a0`
- Peer configuration hash: `793d485232a4e4bbd74613f2d7431a8f1132d96c97d251d61ce451a54b9da36e`
- Quality configuration hash: `1087becc48fecf9b627aafd8e2e5aeb65660c74266cbaa76b5ea89e2b186157b`
- Immutable Phase 2 input database hash: `678d07fcd1c82d5737f44ebd40b57e7d09da4479a62ca6e8150ece55300f2246`
- Final local feature database hash: `6863c5da7ace401853ce623b02fb7f919a53309c91cd4d7362d812cb7a8620b6`
- Local feature database size: 3,118,215,168 bytes; git-ignored and reproducibly rebuilt

## Build and feature results

Fifteen ordered SQL files created the source snapshot, protected base/lag layer, seven feature families, temporal features, peer groups, feature-specific peer fallbacks, quality tables, controls and reporting views.

| Category | Features |
|---|---:|
| Capital | 8 |
| Asset quality | 10 |
| Earnings | 13 |
| Liquidity | 3 |
| Funding | 10 |
| Concentration | 12 |
| Growth | 9 |
| **Total** | **65** |

- Input bank-quarter rows: 698,804
- Feature rows: 698,804
- Feature-quality rows: 698,804
- Peer-group rows: 698,804
- Unique feature keys: 698,804
- Institutions: 11,073
- Peer benchmark rows: 18,393,982 across 27 eligible features
- Full-availability features: 2; features below 1% missing: 29. Screening flags remain null when the supporting history is unavailable rather than implying a clean observation.
- Highest missingness: 11.476%, driven by required eight-quarter history and underlying proxy availability
- Conditional source features built: zero
- Unsupported candidates documented: 13

Unsupported features include regulatory capital ratios/buffers, allowance and provision measures, brokered/uninsured deposits, broader short-term borrowing, and agricultural concentration because their inputs were not in approved Core-v1. No substitute was fabricated.

## Denominators, extremes and quality

| Evidence | Count |
|---|---:|
| Insufficient-lag denominator events | 11,073 |
| Missing denominators | 12,082 |
| Zero denominators | 5,588 |
| Negative denominators | 289 |
| Preserved extreme rows | 1,805 |
| Suspected unit rows | 0 |
| Identifier-continuity warning rows | 4,947 |
| Source-field warning rows | 745 |

Feature exceptions by severity: Informational 77,022; Low 1,805; Medium 5,877; Critical 0; High 0. Invalid features are null and flagged; source values and extreme calculated values remain unchanged.

## Peer benchmarks

- Detailed bank groups: 688,584 bank-quarters; broad asset fallback: 10,220.
- Detailed feature groups: 18,133,416 benchmark rows; feature-specific broad fallback: 260,566.
- Median peer count: 765; range: 1–3,220.
- Rows still below 20 peers after broad fallback: 93,890. These remain flagged and are excluded from later modelling eligibility.
- Percentile bounds and same-quarter isolation controls passed.
- Risk directions are explicit; descriptive/non-monotonic features do not receive an adjusted risk percentile.

## Temporal validation

- Rows with exact prior quarter: 687,731.
- Rows with exact year-ago quarter: 655,157.
- Future prior dates: zero.
- Future year-ago dates: zero.
- Eight-quarter statistics require eight valid trailing observations; no centered windows or full-sample normalization were used.

## Tests and idempotency

- Command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Result: 102 passed: 32 Phase 3 tests plus all 70 prior tests.
- SQL blocking controls: 10 passed.
- Python structural validations: 9 passed.
- No infinite feature values and no invalid percentiles.
- Consecutive build feature rows identical: true.
- Consecutive peer benchmark rows identical: true.
- All 12 exported report hashes identical: true.

As with Phase 2, DuckDB physical-file metadata may change the binary hash across fresh builds. Logical idempotency is based on exact keys, counts, controls and deterministic report hashes; the manifest records the current artifact hash.

## Immutable verification

The Phase 2 database hash remained unchanged before and after the build. All prior raw, anchor, panel and SQL-model immutability tests passed. The Phase 2 database was attached read-only; Phase 3 wrote a separate database.

## Files created

- Three frozen configurations under `configs/`
- Fifteen SQL files under `sql/phase3/`
- Feature builder, validator, reporting and manifest modules under `src/features/`
- Build, validation, export, analysis, configuration and dictionary scripts
- Twelve required Phase 3 CSV reports
- Feature-build run manifest
- Thirty-two Phase 3 tests
- Methodology, dictionary, denominator, peer, control, SQL-learning, completion and readiness documents

## Key commands

Phase 2 was reviewed, committed and tagged; `phase3-risk-features` was created. Configurations were generated and hashed, the feature database was built transactionally, reports exported, results analyzed, all tests executed, and a clean idempotent rebuild completed. Nothing was pushed publicly.

## Remaining risks

- The asset-quality ratios use broad past-due/nonaccrual asset fields against a loan denominator and are explicitly named as proxies.
- HHI covers six reported categories; coverage is stored and incomplete-category HHI is not a complete portfolio measure.
- Current bank class and accounting categories can change through history.
- Growth may reflect mergers or transfers; it is not causal evidence of risk.
- Small broad peer groups remain for rare large-bank/feature/quarter combinations.
- Phase 4 needs a strict point-in-time failure-label policy and must keep assistance and structural exits separate.

Phase 3 stops here.
