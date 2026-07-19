# Phase 0 Completion Report

## Status

**Complete with controlled open items.** Phase 1 may begin with limited anchor-quarter validation; a full historical download remains gated on those checks.

## Files created

- `.gitignore`
- `AGENTS.md`
- `CHANGELOG.md`
- `README.md`
- `SOURCE_MANIFEST.md`
- `configs/phase1_candidate_financial_fields.yaml`
- `docs/DATA_DICTIONARY.md`
- `docs/FDIC_FIELD_SELECTION.md`
- `docs/PHASE0_SOURCE_AUDIT.md`
- `docs/PROJECT_SPECIFICATION.md`
- `docs/PHASE1_DOWNLOADER_PLAN.md`
- `docs/PHASE0_COMPLETION_REPORT.md`
- `scripts/profile_sources.py`
- `scripts/inspect_workbook.mjs`
- `reports/phase0_source_profile.json`
- `reports/phase0_workbook_inspection.json`
- 11 standardized immutable raw-source copies listed in `SOURCE_MANIFEST.md`

## Files modified

None existed in the new project before Phase 0.

## Commands executed

- Located all expected source files and inspected file signatures/headers.
- Created the required project folders.
- Copied source files with `Copy-Item` to standardized paths.
- Initialized Git with `git init --initial-branch=phase0-source-audit`.
- Calculated SHA-256 hashes for originals and copies.
- Ran `scripts/profile_sources.py` twice: initial audit and corrected preamble/YAML-property audit.
- Ran `scripts/inspect_workbook.mjs` twice: structural inspection and full reference-table extraction.
- Queried the official FDIC documentation and open-data policies for source and redistribution context.

## Validation run

- Required source count: **11 of 11 present**.
- Copy/hash equality: **11 of 11 passed**.
- File signatures: **6 CSV, 4 YAML, and 1 valid ZIP-based XLSX passed**.
- CSV exact duplicate scan: **0 exact duplicates across all six CSVs**.
- Financial sample bank-quarter uniqueness: **4,287 rows, 4,287 unique `CERT`, one report quarter**.
- Workbook inspection: **8 sheets**, including 2,333 reference-variable rows plus header.
- Definition property counts: institution 151, failure 21, history 176, financial 2,378.

## Failures

No command or integrity check failed. The initial profiler interpreted the institution-definition preamble as a one-column header and counted only top-level YAML properties; the profiler was corrected and rerun. Raw data was not changed.

## Unresolved questions and Phase 1 gates

- Historical continuity of all 50 candidate fields is not proven by a one-quarter sample.
- Nine candidate fields are absent from the sample and require anchor-quarter API probes.
- `EQV`, `NIM`/`NIMY`, and `DEPUNINS` definition inconsistencies require source reconciliation.
- History extract columns must be reconciled against the smaller definition table.
- Raw redistribution must remain pending until the formal publication review.

## Required confirmations

- Raw downloaded originals remain unchanged: **confirmed by matching SHA-256 hashes**.
- Raw project copies remain unchanged after copying: **confirmed by rehash**.
- Future leakage introduced: **none; no labels, features, preprocessing, or models exist**.
- Unsupported claims introduced: **none**.
- Official CAMELS claim made: **no**; only “public-data CAMELS-style risk indicator framework” is used.
- Historical download begun: **no**.
- Modelling begun: **no**.
- Git commit created: **no**.
- Public push performed: **no**.

