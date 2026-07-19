# Model Calibration Methodology

The base model is fitted on 2001–2013. Calibration is fitted on 2014–2016 and selected on 2017–2018. Candidates are uncalibrated scores, Platt scaling, and isotonic regression when at least 20 calibration positives exist.

Isotonic calibration minimized the preregistered Brier score for the primary model and was frozen. The final selection interval contained only 15 failures. Isotonic ties reduced PR-AUC versus raw and Platt scores, and its calibration slope remained weak. Accordingly, dashboard readiness must decide whether to show a ranking percentile rather than claim precise failure probabilities.
