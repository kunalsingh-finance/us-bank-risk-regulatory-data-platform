# Phase 1 Historical Downloader Plan

## Objective

Build a resumable FDIC BankFind Suite downloader for quarterly institution financial data from 2001 Q1 through the latest consistently available completed quarter, plus institution, failure, and history reference extracts. Phase 1 will not calculate risk features or labels.

Official documentation: https://api.fdic.gov/banks/docs.

## Stage 1: bounded validation before full history

1. Query API metadata with a minimal field set and `limit=1` to confirm endpoint behavior and total counts.
2. Probe six anchor quarters: 2001 Q1, 2004 Q1, 2009 Q1, 2014 Q1, 2020 Q1, and the latest completed consistent quarter.
3. Test all 50 candidate fields and record missingness, absent fields, type drift, unique certificates, and definition breaks.
4. Compare the latest anchor quarter against the 2026 Q1 sample when the dates match.
5. Stop on missing identifiers, materially conflicting definitions, unexplained row-count gaps, or unreliable dates.

## Endpoint plan

| Dataset | Endpoint | Selection | Primary order/key |
|---|---|---|---|
| Financials | `/banks/financials` | One `REPDTE` per quarterly job; FDIC-insured population; compact fields | `CERT`, `REPDTE` |
| Institutions | `/banks/institutions` | Current and inactive institutions needed for the panel | `CERT` |
| Failures | `/banks/failures` | Complete official failure list for linkage | `CERT`, parsed `FAILDATE` |
| History | `/banks/history` | Events needed to classify mergers, exits, and identifier changes | `ID`, `TRANSNUM`, `EFFDATE` |

## Pagination contract

- Use deterministic `sort_by` and `sort_order` with explicit `limit` and `offset`.
- Read the API metadata total before paging.
- Maintain `(endpoint, filters, fields, sort, limit, offset)` as the page identity.
- Hash the canonical request and response body.
- Reject a repeated page hash at a new offset unless the API total and content prove it valid.
- Deduplicate only exact source row IDs during validation; do not silently discard duplicate bank-quarter records.
- Reconcile downloaded rows, unique page identities, and API metadata total before marking a run complete.

## Reliability controls

- Explicit connection and read timeouts.
- Bounded exponential backoff with jitter for timeouts, 429, and retryable 5xx responses.
- Respect `Retry-After` when present.
- Warn with structured request context on each retry, then raise the last error.
- Never retry schema errors, invalid filters, or non-retryable 4xx responses.
- Write each response to a temporary file, validate and hash it, then atomically promote it to the cache.
- Checkpoint after every accepted page and resume from the first missing/invalid page.
- Cache raw API responses by endpoint, reporting quarter, request hash, and page offset.

## Validation contract

Each page and completed quarter must pass:

- Successful status and expected content type.
- Parseable JSON or CSV with all required identifiers.
- Metadata total and pagination bounds.
- Expected requested fields or an explicit, reviewed absence.
- No malformed quarter dates.
- No empty page before the expected final page.
- No exact repeated page at a different offset.
- No duplicate `CERT × REPDTE` after quarter assembly.
- Source and assembled-file SHA-256 hashes.
- Row-count reconciliation to the API total and prior-run tolerance checks.

## Manifest and lineage

Each ingestion run will record:

- Run ID, model-free configuration version, UTC timestamps, endpoint, filters, fields, sort, limit, and offset.
- HTTP status, retry count, response bytes, response hash, row count, metadata total, and cache path.
- Quarter-level assembly hash, record count, unique `CERT` count, schema fingerprint, and validation status.
- Source definition hashes from `SOURCE_MANIFEST.md`.

## Latest-quarter rule

Do not assume the most recent calendar quarter is complete. Query available reporting dates and choose the latest quarter for which:

- The reporting date is a valid quarter end.
- The source is beyond the expected FDIC reporting lag.
- Population and mandatory-field completeness are consistent with adjacent quarters.
- No API release note or metadata issue indicates partial publication.

## Planned files for Phase 1

- `src/ingestion/fdic_client.py`
- `src/ingestion/download_financials.py`
- `src/ingestion/download_institutions.py`
- `src/ingestion/download_failures.py`
- `src/ingestion/download_history.py`
- `configs/fdic_download_config.yaml`
- `scripts/download_fdic_data.py`

These files are planned, not created in Phase 0.

