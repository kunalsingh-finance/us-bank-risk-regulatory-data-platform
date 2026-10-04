# Phase 7 Completion Report

## Outcome

Phase 7 produced publication-safe release candidate `1.0.0-rc1` on branch `phase7-public-release`. Phase 6 was protected at commit `d0b877f` with tag `phase6-dashboard-alerts-complete`. Nothing was pushed, released, or deployed.

Final verdict: **Approved for a manual public-release decision with restricted claims and fresh-history requirement.**

## Publication inventory

- Repository artifacts inventoried: 3,342
- Included authored/public artifacts: 348
- Raw artifacts excluded: 2,734
- Generated binaries/full generated datasets excluded: 137
- Aggregate-only report decisions: 115
- Local metadata exclusions: 8
- Open manual-review decisions: zero

Raw FDIC CSV/API/workbook/definition copies remain local because explicit redistribution permission was not established. Official links, source-download code, configurations, SQL, and mappings are included. Full financial and peer panels remain reproducible local artifacts.

## Artifact and model policy

- Demo institution rows: deterministic synthetic records only; 100 banks × eight quarters = 800 score rows.
- Validation evidence: frozen aggregate tables only; exact governed metrics preserved.
- Active-bank rankings and real institution-level model outputs: excluded.
- DuckDB files and serialized model artifacts: excluded; hashes and methods retained.
- Code license: MIT for project-authored code/documentation only.
- Data/package boundaries: documented in the redistribution review and third-party notices.

## Scans and claims

- Secret scan: PASS, zero findings.
- Local/personal-path scan: PASS, zero findings in the candidate.
- Metadata/unsupported-binary scan: PASS, zero findings.
- Public claims audit: PASS, zero unresolved misleading claims.
- Dependency/license review: PASS for externally installed pinned packages; no vendored third-party code.
- Git-history review: no credential-bearing remote or recognized secret pattern. Four blobs over 5 MB remain in private development history and are excluded from the clean candidate.

The development history must not be published as-is. Initialize any public repository from the clean candidate with fresh history; do not rewrite the private history automatically.

## Reproducibility and tests

- Fresh CPython 3.11.9 environment: PASS.
- Exact pinned dependency install: PASS.
- Environment validation: PASS.
- Public tests in clean candidate: 31 passed.
- Full applicable development suite: 242 passed.
- Ruff public-source check: PASS.
- Full pipeline plan/configuration validation: PASS; no Phase 7 execution of the locked test.
- Public quality gate: PASS.
- Live clean-candidate dashboard: eight of eight pages passed, representative filter passed, zero tracebacks, zero console errors.
- Browser/server shutdown: PASS.

## Immutable evidence

Verified unchanged after all tests:

- Historical panel SHA-256: `94d360d8e39c86658350e5b981d389e0d4c3c48376dc89adaa223caf6ef0232c`
- Phase 3 database: `6863c5da7ace401853ce623b02fb7f919a53309c91cd4d7362d812cb7a8620b6`
- Phase 4 database: `ef298cc2fe13549b673f8c93d33da142b1a8bbb0c7b58cbaff4fb4095d0604b0`
- Phase 5 database: `a57c8e00240f389fafa36d8440bc53494c916d8c4b4098b9eb7d17aea2078cc2`
- Selected model artifact: `da032d45f4db5578dfe2f29b2717eb8c16a48a4722343e79d7c151ca45991276`
- Protocol and model-feature configurations/manifests: no Git diff.

## Files created

Created public demo datasets/dictionaries/manifests, release audit/build/validation modules and scripts, public tests, dependency pins, Make targets, GitHub templates/workflows, license/notices/policies, research/model/validation documentation, architecture/reproducibility guides, publication inventories/scans, release notes, clean-candidate evidence, and readiness reports.

## Files modified

Updated `.gitignore`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, and `src/dashboard/app_pages.py`. Existing generated report CSVs were removed from Git tracking with `git rm --cached` but remain unchanged on local disk; reviewed aggregates were copied to `public_release/reports/`.

## Principal commands executed

- Git status/diff/tag checks; Phase 6 commit/tag; Phase 7 branch creation
- Public demo build and deterministic hash validation
- Publication inventory, Git-history review, security/path/metadata/claims scans
- Environment plan validation and public/full test suites
- Fresh virtual-environment creation and pinned dependency installation
- Ruff checks and public quality gate
- Explicit-allowlist clean-candidate build
- Streamlit demo startup, eight-page browser audit, interaction checks, and clean shutdown

## Remaining restrictions

1. Do not publish the private development Git history; start fresh from the clean candidate.
2. Do not add excluded raw, full-panel, peer, model, database, or real institution-level output artifacts.
3. Do not present PR-AUC as precision, lead with the 289.3× ratio, or describe ranks as probabilities.
4. Always disclose 17 locked-test failures, weak calibration, wide uncertainty, subgroup instability, and false alerts.
5. Re-review current FDIC terms before any future source-data redistribution.
6. Publication and deployment still require separate manual approval.

Release readiness: **Approved with restricted analytical claims.**
