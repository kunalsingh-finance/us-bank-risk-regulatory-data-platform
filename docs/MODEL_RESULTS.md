# Phase 5 Model Results

## Decision

The four-quarter FDIC-failure model is approved as a **ranking model only**. It separates risk materially better than prevalence, but its locked-test calibration is not adequate for presenting scores as precise probabilities.

## Frozen primary model

The selected model is constrained histogram gradient boosting: learning rate 0.05, 150 iterations, 15 maximum leaf nodes, minimum leaf size 50, and L2 regularization 1.0. It uses 47 approved predictors, isotonic calibration, a validation-selected F2 threshold of 0.157143, and a primary top-5%-within-quarter review budget.

Random forest led average rolling-origin PR-AUC (0.489639), while the selected booster led the separate 2014–2018 validation comparison (PR-AUC 0.507937). This disagreement is retained as evidence of temporal instability. In the smaller 2017–2018 calibrated selection window, PR-AUC was 0.261357 with 15 positives.

## Locked test: four-quarter FDIC failure

The 2019 Q1–2024 Q4 test contains 113,117 bank-quarters, 58 positive observations, and 17 unique failing banks.

| Measure | Result |
|---|---:|
| PR-AUC | 0.148342 |
| No-skill PR-AUC / prevalence | 0.000513 |
| PR-AUC lift | 289.3× |
| ROC AUC | 0.794209 |
| Brier score | 0.000604 |
| Calibration intercept | -4.188 |
| Calibration slope | 0.315 |
| ECE | 0.001099 |
| Institution-clustered PR-AUC 95% interval | 0.0353–0.3164 |

The discrimination result is meaningful, but uncertainty is high. The calibration slope and intercept show strong probability miscalibration, and the model Brier score is not better than a near-constant prevalence forecast. Display calibrated percentiles or tiers, not failure probabilities.

## Alert-budget results

| Same-quarter budget | Alerts | False alerts | Positive-quarter recall | Unique failures captured | Event capture 95% interval |
|---|---:|---:|---:|---:|---:|
| Top 1% | 1,143 | 1,110 | 56.9% | 10/17 (58.8%) | 35.3%–82.4% |
| Top 5% | 5,670 | 5,637 | 56.9% | 10/17 (58.8%) | 35.3%–82.4% |
| Top 10% | 11,324 | 11,287 | 63.8% | 12/17 (70.6%) | 47.1%–94.1% |

Median first-alert lead time among top-5%-captured events is 284 days. The identical top-1% and top-5% event capture reflects isotonic score ties; increasing the budget added false alerts without capturing another failure event.

## Stability and subgroups

Annual PR-AUC ranged from 0.546 in 2019 and 0.653 in 2020 to 0.0011 in 2022 and 0.0026 in 2024. No positives occurred in 2021. This is not stable enough for an unqualified performance claim.

Among groups with at least ten positive observations, locked-test PR-AUC was 0.313 for banks below $100 million, 0.144 for $100–500 million, and 0.0149 for $50–250 billion. Several asset bands and most yearly/class subgroups have too few events for reliable conclusions.

## Secondary outcomes

The eight-quarter failure model achieved PR-AUC 0.190036 versus prevalence 0.001066, with ROC AUC 0.761547. Its calibration slope was 0.542 and remains inadequate for probability claims.

The deterioration sensitivity model achieved PR-AUC 0.505768 versus prevalence 0.084895 and ROC AUC 0.835306. It predicts a research deterioration definition, not FDIC failure or an official supervisory outcome.
