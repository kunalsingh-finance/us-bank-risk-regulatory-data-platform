# Full Historical Extraction Methodology

## Scope

Phase 1B extracted the approved FDIC Financials API Core-v1 contract for every quarter from 2001 Q1 through 2026 Q1. The scope is ingestion only. No ratio construction, lags, imputation, failure labels, macroeconomic data, SQL analytical modelling, or predictive modelling is present.

The frozen configuration is `configs/full_historical_extraction.yaml`. It contains 101 exact quarter-end dates, 40 ordered Core fields, the API endpoint and population filter, pagination and retry settings, output locations, lineage versions, run ID, and configuration hash.

## Governing query

The ordered fields are:

```text
CERT,RSSDID,NAMEFULL,REPDTE,STALP,BKCLASS,REGAGNT,ACTIVE,ASSET,
EQ,EQTOT,LNLSGR,LNLSNET,P3ASSET,P9ASSET,NAASSET,ORE,
CHBAL,SC,DEP,DEPDOM,DEPCSBQ,FREPO,OTHBFHLB,
LNRECONS,LNREMULT,LNRERES,LNCI,LNCON,LNCRCD,
NIMQ,NIMYQ,NETINCQ,NONIIQ,NONIXQ,PTAXNETINCQ,ROAQ,EEFFQR,INTEXPYQ,NTLNLSQ
```

The approved population filter is:

```text
ACTIVE:1 AND !(BKCLASS:NC) AND REPDTE:<quarter-end YYYYMMDD>
```

No conditional, replacement, derived, removed, or unresolved field was added. In particular, `EQV`, `NIM`, `NIMY`, and `DEPUNINS` remain excluded under the Phase 1 decisions.

## Frozen configuration and run identity

- Run ID: `phase1b-20260716t173023z`
- Configuration hash: `e680eac0d1308b10900afb570976d193b9869c0d293ba5bb414f8c7279ca7c37`
- Configuration-hash method: SHA-256 over canonical UTF-8 JSON before the `configuration_hash` member is added
- Downloader version: `phase1b-1.0.0`
- Schema version: `fdic-financials-core-v1`
- Normalization version: `source-text-v1`
- Concurrency: one quarter at a time
- Page size: 1,000
- Ordering: `CERT ASC`
- Randomness: none

## Immutable raw layout

Phase 1 anchor responses already occupied six quarter directories and are immutable. The Core-v1 full-history archive therefore uses a versioned child folder without modifying the anchor evidence:

```text
data/raw/api/financials/<YYYY_Q#>/core_v1/
```

Each Core-v1 directory contains raw API page JSON, page manifests and hashes, request parameters, checkpoint, download manifest, combined source JSONL, source-only normalized CSV, schema, missingness, duplicate report, validation result, and a final completion marker.

The completion marker is written last. A quarter without a valid marker bound to the frozen configuration hash is partial and must resume or fail; it is never treated as complete.

## Request and failure controls

Requests are sequential and use bounded exponential-backoff retries for timeouts, connection failures, HTTP 429, and server errors. Every request is logged. Checkpoints are written after each accepted page and are bound to the deterministic query hash.

The supported terminal states are `PASS`, `PASS_WITH_WARNINGS`, `FAIL_RETRYABLE`, `FAIL_SCHEMA`, `FAIL_INCOMPLETE`, `FAIL_DUPLICATE`, `FAIL_IDENTIFIER`, and `FAIL_UNKNOWN`. A failed quarter preserves raw evidence and prevents combined-panel construction.

## Quarter validation

Every completed quarter must satisfy all of the following:

- Requested reporting date on every row
- Parseable, nonmissing `CERT`
- Reported and monitored `RSSDID`
- All 40 Core fields returned and no Core field entirely null
- Numeric fields parse as finite decimals without silent coercion
- Unique `CERT`-`REPDTE` key
- Nonzero row count
- API metadata total equals assembled page rows
- Every page hash matches its manifest
- Stable deterministic output ordering
- Final JSONL, source-normalized CSV, and lineage-normalized CSV hashes recorded
- Existing valid raw files never overwritten with different content

Missing source values remain missing. Extreme values and sparse values are preserved and reported, never removed or winsorized.

## Normalization and lineage

Source values are stored as UTF-8 text in normalized ingestion files after strict numeric validation. This preserves the exact API representation and prevents an early floating-point or null-coercion decision. Phase 2 must apply explicit typed casts under documented SQL controls.

The combined ingestion-stage panel adds only these lineage fields:

- `ingestion_run_id`
- `source_endpoint`
- `requested_quarter`
- `source_page_count`
- `source_manifest_path`
- `extraction_timestamp`
- `downloader_version`
- `configuration_hash`
- `quarter_raw_hash`
- `normalization_version`
- `validation_status`

No financial value is changed by lineage enrichment.

## Combined panel

The combined panel is:

```text
data/processed/ingestion_stage/fdic_financials_2001q1_2026q1.parquet
```

It contains 40 source columns and 11 lineage columns, is sorted deterministically by quarter and `CERT`, and reconciles exactly to the sum of the 101 approved quarter files. A combined CSV was not created because it would duplicate a large uncompressed ingestion artifact without adding validation value; the 54.36 MB Zstandard-compressed Parquet is the frozen combined output.

## Reproduction sequence

```powershell
python scripts\prepare_full_historical_extraction.py
python -m unittest discover -s tests -p "test_*.py" -v
python scripts\run_full_historical_extraction.py
python scripts\audit_full_historical_extraction.py
```

The extraction command is idempotent. A completed rerun verifies all quarter evidence, skips all 101 network extractions, rebuilds the reports and deterministic Parquet, and requires the combined hash to remain unchanged.
