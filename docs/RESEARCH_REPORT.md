# Research Report

## 1. Executive summary

This project tests whether public FDIC financial and structural information can support an auditable relative ranking of bank failure risk. It builds a controlled data platform before modelling: source hashes, complete quarterly extraction, DuckDB reconciliation, public-data CAMELS-style indicators, same-quarter peers, censoring-aware labels, chronological validation, and governed dashboard presentation.

The selected model achieved a locked-test PR-AUC of 0.148342 against a 0.000513 no-skill baseline, ROC AUC of 0.794209, and captured 10 of 17 unique failures within the top 5% of quarterly rankings. The result is useful only as ranking evidence. It is not 14.8% precision, calibration was weak, the event count was small, and subgroup results were unstable.

## 2. Research question

Can transparent features derived from public FDIC filings rank near-term FDIC failures above eligible non-failure observations in future chronological periods while preserving data, label, and model-governance controls?

## 3. Data sources

The source layer uses FDIC BankFind Suite institutions, quarterly financials, failures, and structural-history data. Assistance transactions, failures, mergers, acquisitions, charter changes, and other exits remain distinct. No confidential supervisory information or official CAMELS rating is used.

## 4. Source audit

Phase 0 copied 11 inputs without altering their bytes, recorded SHA-256 hashes, inspected definitions, and identified field conflicts. Phase 1 resolved or excluded ambiguous fields—especially equity, net-interest-margin, and uninsured-deposit definitions—before broad extraction.

## 5. Historical extraction

The production downloader retrieved 101 complete quarters from 2001 Q1 through 2026 Q1. Page manifests, retry/checkpoint logic, schema checks, row reconciliation, duplicate checks, and deterministic hashes produced 698,804 unique bank-quarter rows across 11,073 institutions. A rerun produced the same combined-panel hash.

## 6. DuckDB data model

Raw, staging, core, quality, audit, and reporting schemas separate preservation from interpretation. The canonical fact key is `(CERT, reporting_date)`, with RSSDID as a secondary identifier. Source-to-staging and staging-to-core row counts reconcile exactly. Current institution attributes are not silently forward-filled into history.

## 7. Data-quality controls

SQL controls preserve duplicate candidates, parse exceptions, unmatched identifiers, plausibility warnings, temporal anomalies, and source lineage. Exceptions are classified rather than deleted. No source financial value is imputed.

## 8. Public-data CAMELS-style indicators

The feature layer contains 65 documented measures across capital, asset quality, earnings, liquidity and funding, concentration, growth, and temporal behavior. These are public-data CAMELS-style indicators—not supervisory components or ratings. Denominator null, zero, negative, and materiality states are explicit.

## 9. Peer benchmarking

Twenty-seven measures receive same-quarter peer benchmarks. Primary groups combine quarter, asset band, and bank class, with documented minimum sizes and broader fallbacks. 93,890 undersized-peer observations are flagged and excluded from modelling eligibility. Peers never use future institutions.

## 10. Failure labels

Primary outcomes indicate validated FDIC failure strictly after a reporting date and inside four- or eight-quarter horizons. Assistance events are separate. Binary values are null for censored or ineligible rows rather than forced to zero.

## 11. Censoring and competing exits

Dataset-end right censoring and intervening mergers, acquisitions, voluntary closures, and charter conversions are explicit statuses. Bank disappearance alone is not failure evidence. Boundary tests cover same-quarter, exact-horizon, one-day-beyond, gap, and post-event cases.

## 12. Experimental protocol

The protocol froze the outcome, eligible population, feature contract, candidate models, metrics, alert budgets, preprocessing, chronological folds, and locked-test policy before test access. Protocol hash: `f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4`.

## 13. Chronological validation

Training and expanding validation use only earlier quarters. Median imputation and scaling are fit within training data. Random splitting is prohibited because it would mix regimes and future information.

## 14. Candidate models

Candidate evaluation retained interpretable baselines and nonlinear models rather than reporting only the winner. The selected four-quarter model is `hist_gradient_boosting__1`; selection occurred on validation evidence before locked-test access.

## 15. Locked-test results

The locked test spans 2019 Q1–2024 Q4 with 113,117 observations, 58 positive bank-quarter rows, and 17 unique failures. PR-AUC is 0.148342; baseline prevalence PR-AUC is 0.000513; ROC AUC is 0.794209; Brier score is 0.000604. The 289.3× PR-AUC ratio is mathematically correct but denominator-sensitive and is never presented without the small baseline and limitations.

## 16. Calibration limitations

Calibration intercept is -4.188 and slope is 0.315. The scores therefore should not be read as individual-bank probabilities. Presentation converts scores to same-quarter percentile ranks and tiers.

## 17. Event-level capture

The top 1%, 5%, and 10% review budgets generated 1,143, 5,670, and 11,324 alerts. They captured 10, 10, and 12 of 17 unique failing institutions, respectively. Bank-quarter false-alert counts were 1,110, 5,637, and 11,287. Event capture and row-level precision answer different questions.

## 18. Lead time

Among failures reached by the top-5% budget, median first-alert lead time was 284 days. Lead time describes captured events only and does not compensate for missed events.

## 19. Subgroup instability

Performance varied by calendar period and asset band. The institution-clustered bootstrap 95% PR-AUC interval was 0.0353–0.3164, reflecting substantial uncertainty. Sparse event counts make subgroup comparisons descriptive.

## 20. Explainability

Global and local diagnostics identify features associated with rankings. The dashboard's local driver method perturbs one feature to its training median while holding others fixed. It is an association diagnostic, not a causal explanation.

## 21. Dashboard interpretation

The governed interface displays percentiles, ranks, tiers, history, peers, drivers, validation, quality, and limitations. The public version uses synthetic institutions so no active-bank ranking is exposed. Aggregate validation evidence remains unchanged.

## 22. Reproducibility

Configurations, SQL, scripts, manifests, hashes, and tests support exact reproduction from frozen inputs and logical reconstruction from later official downloads. The public demo is directly reproducible from checked-in synthetic Parquet files.

## 23. Limitations

Limitations include rare events, weak calibration, reporting lag, public-data field discontinuities, missing confidential supervisory evidence, temporal and subgroup instability, changing source versions, imperfect peer comparability, and non-causal explanations.

## 24. Ethical and responsible use

The ranking is not suitable for depositor, trading, lending, enforcement, public-accusation, or supervisory decisions. Misuse could harm institutions and users. Context, source verification, uncertainty, and qualified judgment are mandatory.

## 25. Conclusion

The strongest contribution is the governed analytical chain rather than a single performance number. Public regulatory data contained ranking signal in the locked test, but the evidence supports only a research monitoring aid with prominent restrictions—not an official or probabilistic institution-level determination.
