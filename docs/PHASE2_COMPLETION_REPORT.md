# Phase 2 Completion Report

## Decision

Phase 2 passes. Final verdict: **Approved with documented exclusions** for Phase 3 risk-feature engineering.

No risk ratio, predictive label, macro variable, peer percentile, model, alert, or dashboard was created.

## Version control and build identity

- Branch: `phase2-sql-data-model`
- Protected Phase 1B commit: `386d531`
- Tag: `phase1b-full-extraction-complete`
- Build run ID: `phase2-20260716t215215z`
- Build/schema version: `phase2-1.0.0` / `bank-risk-sql-v1`
- Configuration hash: `d5530cfc0cbba22cc0f729fd1fa52834f16f687c3fcd6d7f041c137ab1cc3286`
- Final local DuckDB SHA-256: `678d07fcd1c82d5737f44ebd40b57e7d09da4479a62ca6e8150ece55300f2246`
- DuckDB size: 394,014,720 bytes

The database binary is git-ignored and reproducibly rebuilt. Fresh DuckDB files contain physical metadata that changes the whole-file hash; therefore semantic idempotency is proven by identical table counts, control results, and all eight report hashes. Two consecutive clean builds had different binary hashes but identical report hashes and table counts. The manifest records the exact binary hash of each completed local artifact.

## Immutable inputs

| Input | Rows | SHA-256 |
|---|---:|---|
| Financial Parquet | 698,804 | `94d360d8e39c86658350e5b981d389e0d4c3c48376dc89adaa223caf6ef0232c` |
| Current institutions CSV | 27,836 | `fd2c23f1294dfa001507e0f717375ce7f45f568c49fe2c15143587d9e263ff1b` |
| History events CSV | 352,107 | `f5debb448fdb63cf37b2960a06427e7cbf81dac1954fb4c8c47434d57afeeb98` |
| Failure/assistance CSV | 592 | `9b65cfcc4177c5e2d7aa9f58a95091e5097079debfcbd83e8e0aafc0ebeb6bc1` |

All Phase 0 raw hashes, Phase 1 anchor hashes, and the Phase 1B panel hash passed the 70-test suite unchanged.

## SQL executed

Fifteen ordered files ran transactionally: schema creation; audit tables; four source loads; identifier standardization; institution, financial, history, failure, exit, and lineage builds; data-quality controls; reconciliation views; and public reporting views. The run manifest records the SHA-256 of every SQL file.

## Reconciliation

| Layer | Financials | Institutions | History | Failure/assistance |
|---|---:|---:|---:|---:|
| Source | 698,804 | 27,836 | 352,107 | 592 |
| Staging | 698,804 | 27,836 | 352,107 | 592 |
| Core | 698,804 | 27,836 | 352,107 | 592 |
| Excluded | 0 | 0 | 0 | 0 |

The financial fact has 698,804 rows, 11,073 distinct CERTs, 101 quarter ends from 2001-03-31 through 2026-03-31, zero duplicate canonical keys, and zero missing CERT, RSSDID, or reporting dates.

Identifier results:

- Current institution match: 11,067 / 11,073 (99.9458%); six unmatched historical banks retained.
- Financial CERT with history: 10,856 / 11,073 (98.0403%).
- Failure/assistance match: 584 / 592 (98.6486%).
- Actual failures: 579 source records, 571 matched; assistance: 13, all matched.
- RSSDID concurrent CERT collisions: zero. Sequential multi-CERT RSSDIDs: 56.

History-event reconciliation retained all 352,107 rows and official code/flag evidence. A canonical CERT was unavailable for 10,752 events—10,751 acquisitions/branch transactions and one other event. These are exceptions, not deleted rows.

## Data-quality results

| Severity | Exceptions |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 655 |
| Low | 236 |
| Informational | 13,697 |
| Total | 14,588 |

The main preserved observations are 398 negative-equity rows, 179 gross-loans-over-assets rows, 173 broad percentage outliers, 63 current-inactive-date timing exceptions, 78 CERT/RSSDID changes, 56 sequential RSSDID successions, 2,867 name histories, and 10,752 unresolved history identifiers. No source value was changed or removed.

The apparent 371 later-quarter records for 12 “failed” institutions were traced to `RESTYPE=ASSISTANCE`, not `FAILURE`. After preserving and applying the official source distinction, actual later-quarter post-failure records are zero. Mergers and assistance remain distinct from failures.

## Tests and idempotency

- Command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Result: 70 passed (25 Phase 2 database tests; 45 prior ingestion tests).
- Validations: 15 blocking structural database checks passed.
- Clean rebuild: PASS.
- Consecutive table-row manifests identical: true.
- Consecutive hashes for all eight CSV reports identical: true.
- Transaction rollback, safe temporary replacement, SQL ordering, lineage, exception generation, and immutable input checks passed.

## Files created or modified

- Configuration: `configs/database_build.yaml`
- SQL: `sql/001_create_schemas.sql` through `sql/015_create_public_views.sql`
- Build code: `src/database/` and six Phase 2 scripts
- Database: local `database/bank_risk.duckdb` (git-ignored)
- Audit manifest: `manifests/database_build/run_manifest.json`
- Reports: eight required reconciliation/quality CSVs
- Tests: `tests/database/`
- Documentation: taxonomy, controls, lineage, source mapping, SQL guide, artifact policy, completion, and readiness documents
- Project metadata: `README.md`, `CHANGELOG.md`, `.gitignore`, and `pyproject.toml`

## Commands executed

Key reproducible commands were the Phase 1B commit/tag/branch commands, virtual-environment dependency installation, configuration preparation, database build, database validation, report export/reproduction checks, exception analysis, and the full unittest discovery command. No public push occurred.

## Remaining risks

- Current institution attributes are not historical point-in-time dimensions.
- Branch/acquisition events account for most unresolved history identifiers.
- Sequential identifier changes need point-in-time joins in later work.
- Financial missingness and economically invalid denominators require explicit Phase 3 protections.
- Failure labels, when eventually authorized, must use only `RESTYPE=FAILURE` and a reviewed timing policy.

Phase 3 may begin only within these documented controls. Phase 2 stops here.
