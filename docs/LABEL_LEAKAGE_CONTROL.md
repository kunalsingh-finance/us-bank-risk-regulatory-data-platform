# Label Leakage Control

Predictor features and outcome evidence are physically separated. Phase 4 attaches the Phase 3 feature database read-only and writes a standalone ignored label database.

Automated controls prohibit failure/closing dates, acquiring institutions, fund numbers, future event codes, future feature values, future peer statistics, outcome-window aggregates, distress dates, and label-status fields from `core.bank_quarter_risk_features`. They also verify that no predictor observation occurs at or after a validated failure and that future distress evidence lives only in Phase 4 event/label tables.

The four SQL leakage controls pass with zero violations. Later modelling must join labels to predictors by CERT and predictor reporting date only. Outcome dates may be used for evaluation and lead-time reporting, never as inputs. Chronological splits remain mandatory.
