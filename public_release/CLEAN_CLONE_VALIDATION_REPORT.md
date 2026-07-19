# Clean Candidate Validation Report

## Scope

Release candidate `1.0.0-rc1` was copied to a new temporary directory outside the development repository from an explicit allowlist. The candidate contained project source, SQL, configurations, documentation, selected immutable manifests, public tests, deterministic synthetic demo Parquet files, and reviewed aggregate reports. It did not contain development Git history, raw/source data copies, full panels, full peer tables, DuckDB files, model binaries, real institution-level predictions, caches, or local logs.

The final publication validation was repeated after the private Phase 7 source was protected at commit `8a0b3d436e728d29411f06b27b71ed20171c02db`. The public candidate remains a fresh-history artifact and does not contain that private repository's Git objects.

## Fresh environment

- CPython: 3.11.9
- Environment: newly created virtual environment inside the temporary candidate
- Installation: `requirements-dev.txt`, including exact runtime and developer pins
- Result: PASS
- Environment validation: PASS; 800 synthetic score rows, ten demo Parquet files, and eleven frozen headline metrics reconciled

The first installation attempt was blocked by the execution sandbox's network policy; the approved network retry installed from package indexes successfully. No package was copied from the development environment.

## Tests and quality

- Publication-safe pytest suite: 31 passed
- Full development-repository applicable suite: 242 passed
- Ruff on public release utilities/tests: PASS
- Secret scan: zero findings
- Personal/local-path scan: zero findings
- Unsupported-binary scan: zero findings
- Unresolved public-claim findings: zero
- Raw/full-panel/full-peer/model-binary exclusion: PASS
- Manifest and frozen aggregate metric checks: PASS

## Live dashboard audit

The demo was started with the fresh environment on a local-only port and audited in a browser. All eight pages loaded from publication-safe data:

1. Executive Overview
2. Current Watchlist
3. Bank Detail
4. Peer Comparison
5. Model Validation
6. Synthetic Demonstration Case Studies
7. Data Quality and Lineage
8. Methodology and Limitations

Each page displayed the persistent demonstration and ranking-only notices. Applicable charts and data controls were populated. The watchlist top-1% radio filter changed state successfully; institution-selection controls and dashboard navigation were exercised. The audit found and corrected two direct file references that initially bypassed the demo filename mapping. After restart, all eight pages had zero tracebacks and the browser console had zero errors. Settled page checks completed within approximately 1.2 seconds per local navigation; dashboard startup completed inside the 10-second launch check.

## Reproducibility and shutdown

The full logical-rebuild configuration validated without executing or reopening the governed locked test. The server was stopped cleanly and browser tabs were finalized. Temporary logs were removed. The fresh virtual environment is excluded from the release manifest and is removed from the final candidate after validation.

Final clean-candidate verdict: **PASS — suitable for manual public-release review, subject to the restrictions in the release manifest.**
