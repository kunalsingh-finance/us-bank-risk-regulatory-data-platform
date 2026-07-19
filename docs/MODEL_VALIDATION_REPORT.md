# Model Validation Report

## Scope and independence controls

Validation assesses ranking discrimination, fixed-budget operations, calibration, uncertainty, temporal stability, subgroup behavior, leakage controls, and reproducibility. It preserves all candidate results and negative findings. Model selection used chronological validation; the 2019 Q1–2024 Q4 test remained locked until the protocol and selected model were frozen. Access count is one.

## Population

The locked test contains 113,117 eligible bank-quarter rows, 58 positive bank-quarter rows, and 17 unique failed institutions. A row-level prevalence of 0.000513 is the no-skill PR-AUC baseline. Failure-event counts, not repeated positive quarters, govern event-capture interpretation.

## Discrimination

The selected model's PR-AUC is 0.148342 and ROC AUC is 0.794209. The PR-AUC ratio to baseline is 289.3, but that ratio is driven partly by the very small baseline and is not an accuracy multiplier. PR-AUC does not equal precision at any particular threshold.

## Operational budgets

| Review budget | Alerts | False-alert rows | Unique failures captured |
|---:|---:|---:|---:|
| Top 1% | 1,143 | 1,110 | 10 of 17 |
| Top 5% | 5,670 | 5,637 | 10 of 17 |
| Top 10% | 11,324 | 11,287 | 12 of 17 |

The primary top-5% budget was frozen before testing. Its median first-alert lead time was 284 days among captured events. Seven of 17 failures were not captured at that budget.

## Calibration

Brier score is 0.000604, calibration intercept is -4.188, and slope is 0.315. The low Brier score reflects the rare-event base rate and does not establish good probability estimation. Calibration is weak; numerical scores are unsuitable as failure probabilities. The approved presentation is same-quarter ranking only.

## Uncertainty and stability

The institution-clustered bootstrap 95% PR-AUC interval is 0.0353–0.3164. Year and asset-band results vary materially; some slices contain too few failures for reliable inference. These results prohibit strong subgroup claims and argue for continued monitoring before any broader use.

## Leakage and reproducibility

Controls verify chronological splits, training-only preprocessing, absence of outcome dates and future values in predictors, frozen selection before test access, and immutable prediction/metric hashes. Rebuilds of governed reports and dashboard tables matched exactly.

## Findings

1. The model shows non-trivial relative ranking signal in the locked period.
2. Evidence is statistically uncertain because only 17 unique failures are observed.
3. Weak calibration prevents probability interpretation.
4. Fixed-budget monitoring generates many false alerts.
5. Temporal and asset-band instability limit generalization.
6. The model is acceptable only as a restricted research ranking demonstration with analyst review and prominent warnings.

Validation conclusion: approved for ranking-only research presentation; not approved for probability estimation, official supervision, automated decisions, or production deployment.
