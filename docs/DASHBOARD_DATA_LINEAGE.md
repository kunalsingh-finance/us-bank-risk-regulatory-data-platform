# Dashboard Data Lineage

| Presentation table | Primary lineage |
|---|---|
| `bank_scores` | Phase 5 validation and locked-test primary predictions; Phase 2 identity; Phase 3 peer groups |
| `bank_history` | `bank_scores` joined one-to-one to Phase 3 risk features |
| `current_watchlist` | Latest-quarter top-5% score rows plus linked drivers |
| `driver_explanations` | Frozen model perturbation plus same-quarter peer benchmarks |
| `peer_comparisons` | Configured Phase 3 benchmark features restricted to scored rows |
| `model_validation` | Frozen Phase 5 reports and locked-test curve data |
| `failure_case_studies` | Frozen failure-event capture and locked-test score linkage |
| `data_quality` | Phase 3 feature-quality controls restricted to scored rows |
| `metadata` | Phase 0–6 coverage, hashes, versions, and build IDs |

The builder verifies the Phase 3, Phase 4, Phase 5 model database, and selected model-artifact hashes before and after each run. Parquet hashes and row counts are recorded in `manifests/dashboard_build/run_manifest.json`.
