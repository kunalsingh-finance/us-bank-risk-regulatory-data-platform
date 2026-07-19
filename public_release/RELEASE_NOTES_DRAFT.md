# Release Notes Draft — 1.0.0-rc1

This release candidate presents a governed public-data banking-risk research platform with reproducible FDIC ingestion, DuckDB modelling, 65 public-data CAMELS-style indicators, censoring-aware labels, chronological model validation, and an eight-page Streamlit demonstration.

The public demo contains only deterministic synthetic institution records and frozen aggregate historical validation evidence. Full source copies, generated panels, peer tables, DuckDB files, model binaries, and real institution-level predictions are excluded.

The selected ranking model achieved locked-test PR-AUC 0.148342 against a 0.000513 no-skill baseline and captured 10 of 17 unique failures in the top 5% of quarterly rankings. Calibration was weak, event count was small, and performance varied by year and asset band. Results are ranking-only and provide no official, probability, supervisory, or investment conclusion.

Final publication validation: 31 clean-candidate tests and 242 applicable private-repository tests passed; all eight synthetic-demo dashboard pages and the representative watchlist filter passed with zero final-session browser console errors. The release source was protected privately at commit `8a0b3d436e728d29411f06b27b71ed20171c02db`; private Git history is not included.

This is a draft. Nothing is published, deployed, or released without separate manual approval. The development repository's existing Git history contains excluded generated artifacts; any public repository must start from the clean candidate with fresh history.
