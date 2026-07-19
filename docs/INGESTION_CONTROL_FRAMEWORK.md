# Ingestion Control Framework

## Control objective

The ingestion layer must produce a complete, deterministic, write-once representation of each FDIC query without silently losing pages, coercing invalid values, changing raw evidence, or accepting an unexpected schema.

## Preventive controls

| Control | Severity | Implementation | Failure action |
|---|---|---|---|
| Immutable Phase 0 sources | Critical | Baseline hashes in `SOURCE_MANIFEST.md`; raw API writes use write-once semantics | Stop and raise hash conflict |
| Explicit query contract | High | Base URL, endpoint, filters, fields, sort, page size, timeouts, and user agent are configuration values | Reject missing/invalid config |
| Deterministic ordering | High | Sort by `CERT ASC`; normalized rows sorted numerically by `CERT` | Stop if duplicate bank-quarter keys appear |
| Required identifiers | Critical | Every API record must contain `CERT` and `REPDTE` | Stop the page and run |
| Quarter validation | Critical | Every `REPDTE` must equal the requested anchor date | Stop the page and run |
| Unexpected schema | High | Only requested fields and documented system field `ID` are allowed | Stop the page and run |
| Raw write-once protection | Critical | Existing raw response may be reused only when SHA-256 matches | Raise `ImmutableFileConflictError` |
| Bounded retries | High | Timeouts, connection errors, HTTP 429, and 5xx use bounded exponential backoff; last error is raised | Fail visibly after maximum attempts |
| Non-retryable HTTP errors | High | Other 4xx responses include status, URL, and response body | Stop immediately |

## Detective and reconciliation controls

| Control | Severity | Evidence |
|---|---|---|
| Metadata total reconciliation | Critical | Assembled rows must equal `meta.total` |
| Empty intermediate page | Critical | Empty page before expected total raises failure |
| Duplicate page hash | Critical | Same response hash at another offset raises failure |
| Duplicate bank-quarter | Critical | `CERT × REPDTE` duplicate list must be empty |
| Page manifest reconciliation | High | Offset, limit, row count, API total, response hash, URL, attempts, and index metadata saved per page |
| Checkpoint integrity | High | Query hash binds checkpoint to endpoint/filter/fields/sort/page size |
| Resume | High | Resume begins at `next_offset` and reassembles all saved pages before completion |
| Requested/returned field comparison | High | Missing requested and unexpected fields reported per anchor |
| Numeric parsing | High | API values must be scalar; unsupported nested types stop ingestion; normalized CSV preserves raw scalar text |
| Missingness and zero share | Medium | Per-field, per-anchor counts distinguish null from all-zero sentinels |
| Extreme-value flags | Medium | Broad plausibility limits create exceptions without deleting observations |
| Manual/API reconciliation | High | Per-field exact, rounding, population, timing, and missing classifications for the latest anchor |
| Source lineage | High | Query parameters, page hashes, normalized hash, schema, missingness, duplicates, validation, and run summary are retained |

## Exception handling

`reports/ingestion_exceptions.csv` is the controlled exception register for anchor ingestion. Exceptions remain in the data and are assigned a classification or downstream use restriction. The framework does not silently remove extreme ratios or convert nulls and zero sentinels into one another.

Required fields or identifier failures are not waivable. Definition/regime issues may be resolved only by classifying a field as Conditional, Replace, Derived, Remove, or Unresolved in the versioned field contract.

## Resume and idempotency

- Each query has a deterministic SHA-256 identity excluding page offset.
- A checkpoint records the next offset, expected total, and accepted page hashes.
- A rerun with the same completed checkpoint performs no new HTTP request and reuses identical write-once pages.
- A checkpoint from another query is rejected.
- A final run is complete only after all saved pages are reparsed, totals reconcile, and duplicate keys remain zero.

## Tests

The ingestion tests cover:

1. Multiple-page assembly.
2. Duplicate-page detection.
3. Missing-page failure.
4. Interrupted-run resume.
5. Idempotent repeated runs.
6. Invalid-field/non-retryable response errors.
7. Timeout retries.
8. Retry-limit enforcement.
9. Deterministic hashes and query identities.
10. Unexpected-schema failure.
11. Duplicate bank-quarter failure.
12. Raw write-once protection.

