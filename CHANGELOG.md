# Changelog

## 1.0.0-rc1 — 2026-07-19

- Added a deterministic publication-safe dashboard package containing synthetic institution records and frozen aggregate validation evidence.
- Added public artifact, redistribution, license, security/privacy, responsible-use, AI-assistance, and reproducibility policies.
- Finalized the research report, model card, validation report, architecture, environment setup, and full-rebuild guidance.
- Added public environment, demonstration, inventory, quality-gate, and clean-candidate commands.
- Excluded raw downloads, full panels, DuckDB files, model binaries, and real institution-level predictions from the release candidate.
- Preserved the Phase 5 frozen model, one-time locked-test results, calibration warning, subgroup instability, and ranking-only interpretation.

## Phase 6 — 2026-07-19

- Built nine governed dashboard tables and an eight-page Streamlit research interface.
- Converted scores to same-quarter percentiles and tiers because calibration was weak.
- Added peers, drivers, quality/lineage, limitations, and balanced historical case-study pages.
- Passed 211 applicable tests and exact table/report rebuild checks.

## Phase 5 — 2026-07-18

- Froze chronological splits, feature contract, candidate set, validation selection, and top-5% monitoring budget before one locked-test access.
- Selected `hist_gradient_boosting__1` on validation evidence.
- Recorded locked-test PR-AUC 0.148342, ROC AUC 0.794209, weak calibration slope 0.315, and 10 of 17 unique failures captured in the top 5%.
- Preserved uncertainty, year/asset-band instability, false-alert counts, missed events, and negative findings.

## Phases 0–4 — 2026-07-16

- Audited and hashed source inputs; resolved field definitions before extraction.
- Downloaded and validated 101 quarters and 698,804 unique bank-quarter rows.
- Built the reconciled DuckDB model, 65 public-data CAMELS-style indicators, 18,393,982 same-quarter peer benchmarks, and censoring-aware failure/distress labels.
- Kept failures, assistance transactions, mergers, structural exits, and censored observations distinct.
