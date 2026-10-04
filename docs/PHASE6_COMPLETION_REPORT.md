# Phase 6 Completion Report

## Final verdict

**Approved for controlled dashboard demonstration with persistent ranking-only restrictions.**

Phase 6 stops here. No Phase 5 model, feature, label, split, threshold, or prediction was changed. No macroeconomic ingestion, deployment, public publication, or Phase 7 packaging was performed.

## Version-control protection

- Branch: `phase6-dashboard-alerts`
- Protected Phase 5 commit: `3b75c54c53c0d72f13b85b0db0c3b0c2218c7ab1`
- Protected Phase 5 tag: `phase5-model-validation-complete`
- Protected commit subject: `Complete locked-test bank failure model validation`
- Public push: not performed

## Governed build

- Dashboard build run ID: `phase6-dashboard-v1-20260718`
- Build timestamp: `2026-07-18T18:00:00Z`
- Frozen model version: `hist_gradient_boosting__1`
- Frozen model artifact SHA-256: `da032d45f4db5578dfe2f29b2717eb8c16a48a4722343e79d7c151ca45991276`
- Frozen Phase 5 prediction database SHA-256: `a57c8e00240f389fafa36d8440bc53494c916d8c4b4098b9eb7d17aea2078cc2`
- Dashboard configuration SHA-256: `72a44a6233d616f6c0f18da387caee975cd1cd6a054835a3d3b0214fc9d5914b`
- Risk-tier configuration SHA-256: `b27662cceb5e3a648413c95ce8dd102cf6c190ebd173c63c02adf1b1f091314a`
- Case-study configuration SHA-256: `857e4a89a9c150ed7f973e7a4a06f499ff7b4dc278c98ff7a56b87ea73d0947d`
- Disclaimer configuration SHA-256: `e0a0191ad707ba07586be1c87123ef56265b886c7f72dded22b62cd33dc31486`

All configuration and output lineage is recorded in `manifests/dashboard_build/run_manifest.json`.

## Presentation tables

| Table | Rows | SHA-256 |
|---|---:|---|
| `bank_scores.parquet` | 228,777 | `00082354d48e0e51dde4351f832b5bff636107fca2f10569b0aa12a0be78c7ed` |
| `bank_history.parquet` | 228,777 | `3fdccbe24d79a80b40996acd61a75485cc7ee789e433be3f691e24c6e6029f9c` |
| `current_watchlist.parquet` | 218 | `e866008d3d5b8d9b75916e636833c9e860b81e9d709a528b9666d49a15246cc4` |
| `driver_explanations.parquet` | 686,331 | `73882a4bf65954d3414d1ef6dbb09e354a0f74e8db48fbf3f60673b1d6c0bbc8` |
| `peer_comparisons.parquet` | 1,595,945 | `a602f8f969772ac3a3d4b36f27b1b11f2115b5bb634bcc69802da78275b2deaf` |
| `model_validation.parquet` | 180 | `940f07d4943bd07e04ae11e43d0644f56c1f6210b6c2a3a451c0de39b0a02486` |
| `failure_case_studies.parquet` | 8 | `57d742cb8d88bed36a4e986c2844f8c257ae5148351bebd4b0f20c6ee9ac6808` |
| `data_quality.parquet` | 228,777 | `b1400f16e0d46548d26212ca0df910fb549743844c8516870f0bba129a816d62` |
| `metadata.parquet` | 17 | `e6efa9b533708fd473469d33d2ff2e3330748c264c9d20bfacb25325965bd07f` |

Every table contains the build run ID, dashboard configuration hash, frozen model version, prediction-source hash, source lineage, build timestamp, and validation status. The Streamlit application reads these prepared files only; it does not open Phase 5 development reports, retrain, rescore, or calculate live model outputs.

## Latest-quarter monitoring population

- Supported prediction quarters: 2014 Q1 through 2024 Q4 (44 quarters)
- Unique scored institutions across supported quarters: 6,512
- Latest supported score quarter: 2024 Q4
- Eligible scored institutions: 4,345
- Low tier: 2,172
- Moderate tier: 1,738
- Elevated tier: 217
- High tier: 174
- Highest monitored tier: 44
- Frozen top-1% review population: 44
- Frozen top-5% primary watchlist: 218
- Frozen top-10% review population: 435

Tiers are same-quarter percentile bands, not estimated event likelihoods. The primary watchlist is the exact frozen top-5% monitoring-budget population.

## Local drivers and peer comparisons

- Driver method: single-feature training-median perturbation using the frozen model
- Drivers per scored bank-quarter: three
- Frozen-score reproduction maximum absolute difference: `0.0`
- Driver rows: 686,331
- Same-quarter peer comparison rows: 1,595,945
- Peer matching key: CERT, RSSDID, reporting date, and feature
- Minimum standard peer size: 20 non-null institutions
- Small or missing peer groups: warned, not hidden

Driver text is limited to “factors associated with the institution's model ranking.” It is not causal, supervisory, or determinative.

## Historical cases

The deterministic case library contains seven selected examples plus one transparent unavailable role:

- Short-lead captured failure: First National Bank of Lindsay, CERT 4134, 18-day top-5% lead
- Long-lead captured failure: Ericson State Bank, CERT 18265, 320-day top-5% lead
- Top-1% captured failure: Almena State Bank, CERT 15426
- Missed failure: Silicon Valley Bank, CERT 24735
- False-positive high-ranking institution: The Farmers Bank, CERT 4054
- Small-bank case: Louisa Community Bank, CERT 58112
- Larger-bank case: Silicon Valley Bank, CERT 24735
- Top-5% but not top-1% captured failure: unavailable because the frozen top-1% and top-5% event-capture sets are identical under the governed score-tie behavior

Assistance transactions, mergers, acquisitions, charter changes, and other non-failure exits remain excluded from the failure outcome.

## Frozen model validation displayed

- Locked-test PR-AUC: 0.148342
- Locked-test no-skill PR-AUC: 0.000513
- PR-AUC lift: 289.3 times baseline
- Locked-test ROC AUC: 0.794209
- Calibration slope: 0.315
- Unique locked-test failures: 17
- Unique failures captured at top 1%: 10 of 17
- Unique failures captured at top 5%: 10 of 17
- Unique failures captured at top 10%: 12 of 17
- Median top-5% lead time: 284 days
- Locked-test access count: one

Precision-recall, ROC, calibration, alert-budget, institution-bootstrap uncertainty, lead-time, yearly, and asset-band diagnostics reconcile to frozen Phase 5 outputs. Weak calibration and the small event count are displayed prominently; the interface does not present a probability gauge.

## Controls and test results

- Phase 6 dashboard controls: 35 of 35 passed
- Full applicable repository suite: 211 of 211 passed
- Entry point and all eight pages: Streamlit smoke passed
- Prepared score rows reconciled: 228,777
- Duplicate score keys: zero
- Percentile-bound exceptions: zero
- Locked-test top-budget counts: exact
- Driver frozen-score differences: zero
- Peer quarter/key exceptions: zero
- Chart/reported-metric reconciliation differences: zero
- Unresolved misleading-language findings: zero
- Immutable Phase 3, Phase 4, Phase 5, and model-artifact hashes: passed
- Deterministic rebuild: all nine table hashes and all governed report hashes identical
- Dashboard data-build benchmark: 26.884 seconds on the tested Windows desktop
- Observed Streamlit startup-readiness upper bound: 2.000 seconds
- Representative warm page loads: Executive 0.427 seconds, Bank Detail 1.856 seconds, Model Validation 2.067 seconds; average 1.450 seconds

## Live startup and visual review

The dashboard started successfully at the local Streamlit endpoint and returned HTTP 200. Browser review covered the root entry point and all eight pages. Interactions passed for the watchlist top-1% selector, the Bank Detail feature tabs, and the case-study selector. There were zero substantive browser errors.

Visual review detected and corrected a dark-host contrast issue. The final app uses an explicit light theme, accessible dark text on metrics and governance callouts, a responsive 18-rem navigation rail, and compact heading typography. At the tested 1,280-pixel viewport, document width equalled viewport width with no page-level horizontal overflow. Detailed results are in `reports/dashboard_browser_validation.csv`.

## Files created

- Four governed dashboard configuration files under `configs/`
- Nine prepared Parquet tables under `data/processed/dashboard/`
- Streamlit entry point and eight pages under `dashboards/`
- Functional build, validation, access, ranking, chart, explanation, and manifest modules under `src/dashboard/`
- Five Phase 6 scripts under `scripts/`
- Thirty-five dashboard tests under `tests/dashboard/`
- Twelve required governed reports plus browser and rebuild evidence under `reports/`
- Twelve Phase 6 methodology, control, deployment, limitation, user, completion, lineage, and readiness documents under `docs/`
- Streamlit theme configuration under `.streamlit/`

## Principal commands executed

```powershell
git status
git diff --stat
git add .
git commit -m "Complete locked-test bank failure model validation"
git tag phase5-model-validation-complete
git switch -c phase6-dashboard-alerts
python scripts/prepare_dashboard_configs.py
python scripts/build_dashboard_data.py
python scripts/validate_dashboard_data.py
python -m unittest discover -s tests -v
python scripts/export_phase6_reports.py
python -m streamlit run dashboards/app.py --server.headless=true --server.port=8501
```

No public push occurred.

## Remaining risks and restrictions

1. Only 17 unique failing banks support the locked test.
2. Calibration is weak; use is restricted to relative same-quarter ranking.
3. Performance varies by year and asset band.
4. False positives are expected at any fixed review budget.
5. Small or sparse peer groups can limit comparisons.
6. Public FDIC data cannot reproduce confidential supervisory assessment.
7. Local perturbation drivers are associative and depend on the frozen feature set.
8. The full bank-level presentation tables, raw FDIC archive, and serialized model are not approved for public distribution.
9. The project has not undergone accessibility certification, penetration testing, or production hosting review.
10. Public-release README editing, licensing, redistribution decisions, publication-safe samples, screenshots, and clean-clone validation remain Phase 7 work.

## Phase 7 readiness

**Approved with dashboard restrictions.** Phase 7 public-release preparation may begin only under the restrictions in `docs/PHASE7_PUBLIC_RELEASE_READINESS.md`. This report does not authorize publication or deployment.
