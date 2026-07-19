# Phase 2 Data Lineage

The build is governed by `configs/database_build.yaml` and run ID `phase2-20260716t215215z`. Its configuration hash is `d5530cfc0cbba22cc0f729fd1fa52834f16f687c3fcd6d7f041c137ab1cc3286`.

```text
immutable source files
  -> staging tables (source columns + parse status + record reference)
  -> core tables (approved typing/taxonomy only)
  -> quality exceptions and audit tables
  -> reporting reconciliation views and CSV exports
```

Every core row retains `source_file`, `ingestion_run_id`, `source_record_reference`, `source_sha256`, `build_configuration_hash`, and `sql_version`. Financial rows additionally retain the Phase 1B requested quarter, extraction run, raw-quarter hash, source manifest, extraction timestamp, downloader version, normalization version, and validation status.

`audit.source_files` records the repository-relative path, immutable hash, expected row count, loaded row count, hash status, and build run. `audit.sql_execution_log` records ordered SQL filenames and hashes. `audit.table_build_manifest` records table rows and key counts. `audit.source_lineage` links each core table to its staging and source layers.

The generated DuckDB file is a local build artifact. The authoritative reproducibility chain is the immutable input hashes, frozen configuration, ordered SQL hashes, build manifest, structural validations, and deterministic CSV report hashes.
