# Model Preprocessing Policy

Numeric missing values are median-imputed using the applicable training fold only, with explicit missingness indicators. Linear models additionally use training-fold standardization. Tree models are not scaled. No value is imputed before split assignment; no validation or test observation contributes to a fitted median, scale, or category level.

There is no full-sample clipping, winsorization, feature selection, target encoding, or synthetic oversampling. Raw Phase 3 features remain immutable. `reports/preprocessing_audit.csv` records the selected model's training-only medians.
