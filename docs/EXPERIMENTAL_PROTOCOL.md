# Phase 5 Experimental Protocol

The primary outcome is FDIC failure within four quarters. Failure within eight quarters is secondary; severe deterioration is sensitivity-only. Only `POSITIVE` and `NEGATIVE` label statuses enter binary modelling. Censored, post-event, unresolved, insufficient-history, and data-quality-ineligible rows are excluded.

The frozen predictor contract contains 47 Phase 3-approved public-data CAMELS-style indicators. Identifiers, names, lineage, peer observations below the minimum group size, event/outcome fields, future fields, and the 18 explicitly excluded Phase 3 features are not predictors. The complete contract is in `configs/model_features.yaml`.

Chronological periods are training 2001 Q1–2013 Q4, validation 2014 Q1–2018 Q4, and locked test 2019 Q1–2024 Q4. Three expanding-window folds govern hyperparameter selection. The recent test has few failures, so it is retained as a genuine test with institution-clustered and event bootstrap uncertainty rather than expanded after performance inspection.

Candidate families are prevalence, an interpretable rule score, logistic regression, L1/L2/elastic-net regularized logistic regression, constrained random forest, and constrained histogram gradient boosting. Primary selection uses PR-AUC; ties use Brier score, calibration, recall and event capture at top 5%, then simplicity. Accuracy is descriptive only.

Median imputation, missing indicators, and linear-model scaling are fitted inside each training fold. SMOTE is excluded. Raw values are never overwritten. Calibration candidates are none, Platt, and isotonic; the method is selected without locked-test access by Brier score. The probability threshold maximizes F2 on the final validation-selection window. Operational rankings use the top 5% within each quarter, with top 1% and 10% reported.

The governing machine-readable protocol hash is `f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4`. A v1 preliminary analysis and a timed-out v2 SAGA run were invalidated before any locked-test access. V3 uses deterministic averaged SGD for the regularized-logistic candidates. The locked test may be completed once after the pre-test commit and tag.
