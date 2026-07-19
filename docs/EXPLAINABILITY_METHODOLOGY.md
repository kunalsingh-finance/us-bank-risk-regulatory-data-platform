# Explainability Methodology

Driver explanations use the already-selected frozen histogram-gradient-boosting model. For each scored bank-quarter, the build first reproduces the stored raw score exactly. It then replaces one configured feature at a time with that feature's training-only median and measures the score change. The three largest absolute changes are retained.

This single-feature perturbation belongs to the specific bank-quarter and requires no outcome refitting. A positive delta means the observed value increased the frozen ranking score relative to the training-median reference; a negative delta means it decreased the score. Current values are joined to same-quarter peer medians and percentiles when available. Missingness and small-peer warnings propagate.

The app labels these as “Factors associated with the institution's model ranking.” Perturbations can reflect interactions and correlated inputs and are not causal effects. The build reconciled all 228,777 reproduced raw scores with maximum absolute difference 0.0.
