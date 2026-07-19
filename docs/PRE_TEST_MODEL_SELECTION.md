# Pre-Test Model Selection

Status: **frozen before locked-test access**  
Protocol hash: `f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4`

The primary four-quarter failure model is `hist_gradient_boosting__1` (hist_gradient_boosting) with frozen parameters `{"l2_regularization": 1.0, "learning_rate": 0.05, "max_iter": 150, "max_leaf_nodes": 15, "min_samples_leaf": 50}`. Isotonic calibration was selected by the preregistered Brier-score rule. The probability threshold is `0.15714285714285714` and the primary operational alert budget is the top 5% within each reporting quarter.

Validation selection PR-AUC was 0.261357, versus prevalence 0.000348. Brier score was 0.000309; calibration slope was 0.546. Only 15 positives occurred in the 2017–2018 final selection window, so calibration and threshold estimates are uncertain. Isotonic calibration improved Brier score but introduced ties and reduced PR-AUC relative to the raw ranking. This limitation is frozen and will not be corrected after seeing the test.

Random forest led mean rolling-origin PR-AUC, while histogram gradient boosting led the separate 2014–2018 validation comparison. Family selection followed the frozen validation-only protocol. No locked-test outcome was accessed.

The training and validation datasets, model binaries, calibrators, feature contract, protocol, and governing code are hashed in `manifests/model_experiment/pre_test_selection_manifest.json`. Any completed test access makes this selection immutable.
