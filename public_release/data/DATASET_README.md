# Publication-Safe Demonstration Data

This directory contains deterministic synthetic institution records plus frozen aggregate historical validation evidence.

## Data classes

- `synthetic_bank_quarter_sample.parquet`: 25 illustrative synthetic bank-quarter records.
- `dashboard_demo_scores.parquet`: 800 synthetic rankings for 100 synthetic banks across 2023 Q1–2024 Q4.
- `dashboard_demo_history.parquet`: synthetic feature histories used by charts.
- `dashboard_demo_watchlist.parquet`: five synthetic latest-quarter top-5% examples.
- `dashboard_demo_drivers.parquet`: synthetic associative driver rows.
- `dashboard_demo_peer_comparisons.parquet`: synthetic same-quarter comparisons.
- `dashboard_demo_case_studies.parquet`: synthetic captured, missed, false-alert, and comparator scenarios.
- `dashboard_demo_quality.parquet`: synthetic quality states.
- `dashboard_demo_metadata.parquet`: demo and frozen-research provenance.
- `dashboard_demo_validation.parquet`: frozen aggregate Phase 5 validation evidence; no bank identity or institution-level prediction row.

Institution names follow `Synthetic Bank NNN`; CERT values are 900001–900100; states are `DEMO`; validation status is `DEMONSTRATION_ONLY`. They are not sampled, anonymized, or transformed real banks. No active institution record, raw FDIC record, full peer row, model binary, or probability estimate is present.

The validation aggregates preserve the governed research metrics and must not be attributed to the synthetic examples. `SAMPLE_GENERATION_MANIFEST.json` records deterministic configuration, row counts, sizes, and SHA-256 hashes. `DATA_DICTIONARY.csv` records each field and data class.

The project MIT License covers the project-authored synthetic package. It does not grant rights in external FDIC source data. Use is subject to `RESPONSIBLE_USE.md`.
