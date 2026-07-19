# Phase 5 Completion Report

## Status

Phase 5 passes with the verdict **Approved as ranking model only**. Work stopped before dashboard, public-release, resume, LinkedIn, or interview packaging.

| Item | Result |
|---|---|
| Branch | `phase5-model-development` |
| Phase 4 commit/tag | `7f4f4aa` / `phase4-labels-validation-complete` |
| Pre-test commit/tag | `4a4131a` / `phase5-pre-test-model-frozen` |
| Protocol hash | `f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4` |
| Feature-contract hash | `8cdf6b846f368a42cd7cec3190962da0beb1858f1ad4247bcecb5557dfc8326e` |
| Split-assignment hash | `b332da8386665d474b2759e85e12ec24f9894643ccf1d0e91d7cfb85c8d5e9a7` |
| Selected model | `hist_gradient_boosting__1` |
| Calibration | Isotonic, fitted without test access |
| Frozen F2 threshold | 0.157143 |
| Primary alert budget | Top 5% within quarter |
| Locked-test accesses | Exactly 1 completed |
| Tests | 176 passed |

## Populations and periods

The four-quarter dataset contains 392,897 training observations with 2,060 positives, 115,660 validation observations with 113 positives, and 113,117 locked-test observations with 58 positives. Periods are 2001 Q1–2013 Q4, 2014 Q1–2018 Q4, and 2019 Q1–2024 Q4; modelling eligibility and rolling-history requirements make the earliest used observation 2001 Q4. The locked test contains 17 unique positive banks.

The eight-quarter locked test contains 101,298 observations and 108 positive bank-quarters. The deterioration locked test contains 113,317 observations and 9,620 positives.

## Development evidence

Ten preregistered configurations across six families were evaluated in three expanding-window folds. Random forest configuration 2 led mean cross-validation PR-AUC at 0.489639. Family winners were then compared on the separate validation period, where constrained histogram gradient boosting led with PR-AUC 0.507937. That family difference is documented as instability rather than hidden.

The 2017–2018 validation-selection interval contained only 15 positives. Isotonic calibration minimized Brier score (0.000309) but reduced PR-AUC to 0.261357 through ties and produced a validation calibration slope of 0.546. The model, calibrator, thresholds, alert budgets, data, and code were then frozen.

## Locked-test results

Primary PR-AUC is 0.148342 versus prevalence 0.000513, a 289.3× lift. ROC AUC is 0.794209; Brier score is 0.000604; calibration intercept is -4.188 and slope 0.315. Institution-clustered PR-AUC 95% interval is 0.0353–0.3164.

Top 1%, 5%, and 10% bank-quarter budgets capture 56.9%, 56.9%, and 63.8% of positive observations and 58.8%, 58.8%, and 70.6% of unique failure events. False alerts are 1,110, 5,637, and 11,287. Median top-5% captured-event lead time is 284 days.

Eight-quarter test PR-AUC is 0.190036 versus 0.001066 prevalence. Deterioration sensitivity PR-AUC is 0.505768 versus 0.084895 prevalence. Neither sensitivity result replaces the primary conclusion.

## Reproducibility and controls

The project created frozen protocol, feature, candidate, metric, and access-policy configurations; masked DuckDB model datasets; model and calibration artifacts under a Git-ignored path; model registries; 26 required reports plus supporting reports; and all required modelling modules and scripts. The Phase 3 database hash remains `6863c5da7ace401853ce623b02fb7f919a53309c91cd4d7362d812cb7a8620b6`; Phase 4 remains `ef298cc2fe13549b673f8c93d33da142b1a8bbb0c7b58cbaff4fb4095d0604b0`.

The full suite passed 176 tests. Validation selection, test masking, one-time access, threshold and feature immutability, event capture, cluster bootstrap, serialization, dataset uniqueness, and earlier-phase controls passed. No post-test tuning occurred.

Report-hash export was executed twice and produced the identical manifest hash `ef85be974f44d1f3c319473a86ce9d6f7e514d054a113d229a2f5d5a16cfd99d`.

## Commands executed

Key governed commands were:

```powershell
python scripts/freeze_experiment_protocol.py
python scripts/build_model_datasets.py
python scripts/run_training_cv.py
python scripts/evaluate_validation.py
python scripts/freeze_pre_test_selection.py
python -m unittest discover -s tests -q
git add .
git commit -m "Freeze Phase 5 model selection before locked test"
git tag phase5-pre-test-model-frozen
python scripts/run_locked_test.py
python scripts/finalize_phase5_database.py
python scripts/run_secondary_outcomes.py
python scripts/export_phase5_reports.py
python scripts/validate_phase5.py
python -m unittest discover -s tests -q
```

The initial SAGA-based v2 development run reached the 30-minute limit with non-convergence warnings. It was invalidated before selection and before test access. The v3 protocol was re-hashed before the successful final development run.

## Files created

Phase 5 added five frozen configurations, protocol/selection/report manifests, masked DuckDB modelling datasets, 16 `src/models` modules, ten build/evaluation/validation scripts, 41 Phase 5 tests, the complete required CSV report set, and the modelling/validation/readiness documentation. Generated model binaries and `database/bank_risk_models.duckdb` are Git-ignored and reproducibly built; report and governance artifacts are retained for review.

## Limitations and readiness

The recent test contains only 17 unique positive banks; confidence intervals and subgroup estimates are wide. Calibration is not suitable for probability presentation. Performance varies materially across time and asset bands, score ties reduce budget efficiency, and false alerts are high. The model is approved for Phase 6 only as an explainable ranking demonstration using percentiles or tiers with prominent warnings.
