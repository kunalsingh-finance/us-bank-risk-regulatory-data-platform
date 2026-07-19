# Dashboard Methodology

Phase 6 presents frozen Phase 5 primary-model validation and locked-test scores as relative same-quarter ranks. It does not retrain, recalibrate, rescore new quarters, change the feature contract, or reopen the locked test. Supported scores cover 2014 Q1 through 2024 Q4; the latest prepared monitoring quarter is 2024 Q4.

The build attaches Phase 2–5 DuckDB files read-only, verifies their hashes, selects the primary `failure_4q` prediction rows, and joins identity, validated risk features, quality flags, and same-quarter peers by `CERT`, `RSSDID`, and reporting date. Nine prepared Parquet tables isolate dashboard startup from the analytical pipeline.

Rank percentiles are calculated within each reporting quarter only. Tied scores share percentile and rank. The fixed 1%, 5%, and 10% review budgets use score descending and CERT ascending as the deterministic tie-break. This exactly reconciles the locked-test counts of 1,143, 5,670, and 11,324 bank-quarter alerts.

All presentation tables contain build ID, configuration hash, model version, prediction-source hash, source lineage, fixed build timestamp, and validation status. Every file is hashed in `manifests/dashboard_build/run_manifest.json`.
