# Full Rebuild Guide

## Reproducibility boundary

The repository supports logical reconstruction of the source archive, quarterly panel, DuckDB model, risk indicators, labels, model datasets, chronological experiments, and dashboard tables. Exact hashes are expected only when the same frozen inputs, package versions, configurations, and code are used. The FDIC service may revise historical files or schemas, so future downloads can differ without implying an implementation defect.

## Controlled sequence

1. Review official FDIC terms and available disk space.
2. Create a fresh environment and run `scripts/validate_environment.py`.
3. Inspect `configs/full_pipeline.yaml` and all frozen component configurations.
4. Validate the plan:

   ```powershell
   python scripts\run_full_pipeline.py --config configs\full_pipeline.yaml
   ```

5. In a new rebuild workspace only, set `BANK_RISK_FULL_REBUILD_CONFIRM=YES` and execute the same command.

The locked-test stage is a manual governance boundary. Validation selection must be frozen first, and the test may be accessed once per independent experiment run. Never point a reproduction run at the governed local Phase 5 database or overwrite its evidence.

## Expected scale

The frozen build processed 101 quarters, 698,804 bank-quarter rows, and 18,393,982 peer benchmarks. Allow several gigabytes for raw pages, intermediate data, databases, and reports. APIs should be queried conservatively with checkpointing and resume controls.

Failures, schema drift, hash mismatch, duplicate keys, missing identifiers, or incomplete quarter manifests are blocking. Do not impute source values or silently substitute fields.
