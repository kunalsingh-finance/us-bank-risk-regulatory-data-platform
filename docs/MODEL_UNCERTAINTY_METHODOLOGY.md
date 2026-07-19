# Model Uncertainty Methodology

Observation-level PR-AUC, ROC AUC, and Brier uncertainty use 200 bootstrap resamples clustered by CERT. This preserves within-bank dependence better than independent bank-quarter resampling. Event-level capture uses 200 resamples of unique FDIC failure events, preventing multiple pre-failure quarters from being treated as independent failures.

Intervals are percentile 95% intervals. The locked test includes only 17 positive banks, so intervals may be wide and subgroup estimates with fewer than ten positives are explicitly marked insufficient or cautionary. Bootstrap intervals quantify sampling instability; they do not eliminate temporal-distribution-shift risk.
