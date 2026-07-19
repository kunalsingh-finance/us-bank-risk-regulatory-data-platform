# Model Card

## Model identity

- Name: FDIC four-quarter failure relative-ranking model
- Frozen candidate: `hist_gradient_boosting__1`
- Protocol hash: `f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4`
- Feature contract hash: `8cdf6b846f368a42cd7cec3190962da0beb1858f1ad4247bcecb5557dfc8326e`
- Model artifact hash: `da032d45f4db5578dfe2f29b2717eb8c16a48a4722343e79d7c151ca45991276`
- Status: frozen research evidence; binary intentionally excluded from public release

## Intended use

Retrospective research into whether public FDIC financial indicators can prioritize bank-quarter observations for further analyst review. Output is a same-quarter relative rank.

## Prohibited use

No official supervision, CAMELS rating, calibrated failure probability, depositor decision, public accusation, trading or lending recommendation, enforcement action, or automated adverse decision.

## Data and outcome

The primary label is validated FDIC failure within four quarters. Assistance transactions and structural exits are separate; censored rows are not negatives. Features cover approved capital, asset-quality, earnings, liquidity/funding, concentration, growth, temporal, peer, and quality measures. No confidential supervisory information is used.

## Training and evaluation

Development is chronological with expanding validation folds and training-only preprocessing. The locked test covers 2019 Q1–2024 Q4 and was accessed once after model and top-5% monitoring-budget selection were frozen. The test has 113,117 rows, 58 positive rows, and 17 unique failures.

## Missingness and imbalance

The selected pipeline uses training-only median imputation where contractually allowed; source financial data and feature tables remain unimputed. Conditional/unavailable features and quality failures remain restricted. Evaluation emphasizes PR-AUC, event capture, precision/recall at fixed review budgets, calibration, uncertainty, and temporal/subgroup diagnostics rather than accuracy.

## Locked-test evidence

- PR-AUC: 0.148342; no-skill baseline: 0.000513
- Institution-clustered PR-AUC 95% interval: 0.0353–0.3164
- ROC AUC: 0.794209
- Brier score: 0.000604
- Calibration intercept/slope: -4.188 / 0.315
- Unique failures captured: 10/17 at top 1%, 10/17 at top 5%, 12/17 at top 10%
- Median first top-5% lead time: 284 days

PR-AUC is an area across thresholds, not 14.8% precision. At the top-5% budget there were 5,670 bank-quarter alerts and 5,637 false-alert rows under the frozen label definition.

## Limitations

Only 17 failures support the locked test; confidence intervals are wide. Calibration is weak. Results vary by year and asset band. Reporting data can be revised, delayed, missing, or definition-dependent. Public data omit confidential supervisory information. Drivers are associative. Ranks are relative to an eligible same-quarter population and can change when the population changes.

## Governance

The outcome, features, splits, candidates, metrics, preprocessing, alert budgets, and locked-test policy were configuration-hashed. Frozen artifacts and reports are hash-manifested. No post-test tuning or recalibration occurred. Retraining is not authorized by this release candidate.
