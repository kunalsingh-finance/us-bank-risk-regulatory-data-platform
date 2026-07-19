# Phase 0 Source Audit

## Executive conclusion

All required files were located, copied, renamed, hashed, and structurally inspected. The raw copies match the originals byte for byte. The source set is sufficient to design a Phase 1 historical downloader, but the single-quarter financial sample is **not** sufficient to establish 2001–present field continuity. It contains 41 of the 50 proposed fields; the downloader must request nine additional balance-sheet fields and run an explicit availability scan before the field contract is frozen.

No historical download or modelling was performed.

## Scope and method

The audit used streaming CSV reads, SHA-256 hashing, exact-row fingerprints, candidate-key frequency checks, date-range scans, definition-file inspection, and read-only workbook inspection. Raw files were never opened for writing. The FDIC API documentation identifies `/institutions`, `/history`, `/financials`, and `/failures` as the relevant public endpoints and supplies downloadable schema definitions: https://api.fdic.gov/banks/docs.

## Population and schema findings

| Dataset | Rows | Columns | Exact duplicate rows | Key finding |
|---|---:|---:|---:|---|
| Institutions | 27,836 | 140 | 0 | `CERT` is unique in this extract; `RISDATE` is uniformly 2026-03-31 |
| Financial sample | 4,287 | 161 | 0 | One unique row per `CERT` and `RSSDID` for 2026-03-31 |
| Failures | 592 | 33 | 0 | `CERT` and `ID` are unique; failure date is not unique, as expected |
| History events | 352,107 | 244 | 0 | `ID` is unique; `CERT`, `TRANSNUM`, and dates repeat because one institution or transaction may have multiple event records |
| History definitions | 231 | 3 | 0 | Clean definition table, but 13 extract columns are not represented one-for-one |
| Institution definitions | 152 | 3 | 0 | Requires skipping its title preamble line before CSV parsing |

## Missingness findings

Missingness is structural rather than uniform:

- Failure fields `FSL_PROG` and `BANKNO` are entirely empty; `BRDATE`, `COMMENTS`, and `UNINSDEP` are highly sparse. Core linkage fields `CERT`, `ID`, and `FAILDATE` are complete.
- The financial sample has eight fields that are entirely empty (`NALTOT`, `LSALNLS`, `P9LTOT`, `LSASCDBT`, `MSA_NAME`, `LSAOA`, `LSAORE`, and `P3LTOT`). Several securitization fields are present for only about 2% of banks. This is a business/reporting-population issue, not a reason to impute blindly.
- The history dataset is intentionally wide and sparse because acquiring, outgoing, surviving, former, and office attributes apply only to relevant event types.
- The institution extract contains many obsolete regulatory and change-code fields that are entirely or almost entirely empty.

Complete per-column counts are retained in `reports/phase0_source_profile.json`.

## Identifier findings

- `CERT` is the preferred FDIC institution identifier and is complete and unique within the 2026 Q1 sample.
- `RSSDID` is retained as a secondary Federal Reserve identifier and is complete and unique in the sample.
- `ID` is a source-system row identifier, not the analytical bank key.
- `UNINUM`, `TRANSNUM`, `SUR_CERT`, `OUT_CERT`, and `ACQ_CERT` are essential to reconcile structure events and certificate transitions.
- The analytical key will be `CERT × reporting_quarter`, with a documented crosswalk for certificate and charter changes. Names are descriptive attributes and never the sole join key.

## Date findings

- Financial sample: `REPDTE = RISDATE = 2026-03-31` for all 4,287 rows.
- History extract selection is by `PROCDATE` (2000-01-01 through 2026-07-09), but event `EFFDATE` reaches back to 1884 because related historical records can predate the selection window.
- Dates ending in 9999 are source sentinels for open-ended/unknown dates and must become documented null/open-ended representations in staging, never ordinary calendar dates.
- String min/max values in the failure CSV are not chronological because its dates use multiple display formats. Phase 1 must parse them explicitly and validate against `FAILYR`.

## Definition reconciliation

The definition assets are useful but not internally perfect:

- The financial YAML exposes 2,378 data properties; the workbook reference table exposes 2,333 variable rows plus a header.
- The workbook narrative attached to `EQV` describes uninsured deposits even though both the title and YAML formula define equity capital divided by assets. The YAML formula is the coherent definition; the conflict must be logged.
- `NIM` is labeled as net interest income in the YAML while the sample values can be confused with ratios. The candidate query therefore uses `NIMY`, explicitly defined as net interest margin percentage.
- `DEPUNINS` exists in the YAML and sample but lacks a populated title/definition in the workbook reference. The related `DEPUNA` narrative supplies reporting-threshold caveats, but equivalence must be validated before use.
- Regulatory capital comparability changes after Basel III reporting and the 2020 CBLR election. `IDT1CER`, `IDT1RWAJR`, and `RBCRWAJ` cannot be treated as uninterrupted 2001–present measures.

## Financial sample sufficiency

The sample is sufficient for:

- Confirming API output shape, identifiers, quarter format, and present-day data types.
- Designing pagination, schema validation, row-count controls, and a provisional compact field list.
- Identifying present-day missingness and reporting-population effects.

It is not sufficient for:

- Proving availability or comparability from 2001 onward.
- Determining when field definitions changed.
- Establishing failure-model event counts by period.
- Freezing the model feature list or experiment protocol.

Nine proposed fields are absent from the sample: `LNLSGR`, `OTHBFHLB`, `LNRECONS`, `LNREMULT`, `LNRERES`, `LNCI`, `LNCON`, `LNCRCD`, and `LNAG`. These are present in the FDIC definitions/workbook and should be included in Phase 1 probe queries.

## Redistribution and legal status

The FDIC describes its machine-readable datasets and APIs as free public open data: https://www.fdic.gov/open-government/open-data/. Federal Deposit Insurance Act section 53 requires public data assets to be freely downloadable and API-accessible where appropriate. The FDIC website also disclaims warranties and warns that third-party linked content may have separate copyright restrictions: https://www.fdic.gov/policies/.

Accordingly, the internal raw copies are usable for analysis, but publication remains **pending** until the formal Phase 14 inventory confirms each artifact's source, excludes non-FDIC third-party content, and records the appropriate notices.

## Phase 0 issues and disposition

| Issue | Severity | Disposition |
|---|---|---|
| Definition conflict for `EQV` | High | Use formula/title, log conflict, verify in Phase 1 |
| Ambiguous `NIM` naming | High | Use `NIMY` for margin; do not infer from `NIM` |
| One-line preamble in institution definitions | Medium | Parser skips preamble; raw remains unchanged |
| Sentinel 9999 dates | Medium | Normalize in staging with explicit lineage |
| 13-column difference between history extract and definition table | Medium | Reconcile by exact names before table contract |
| Only one financial quarter supplied | High | Run anchor-quarter availability probes before freezing fields |
| Raw redistribution not yet signed off | High | Keep raw data Git-ignored until Phase 14 |

## Gate decision

**Phase 0 passes with controlled open items.** Phase 1 downloader implementation may begin, but the first execution must be a limited metadata/anchor-quarter validation. A full 2001–latest quarterly download is not authorized until schema, field availability, row counts, and identifier behavior pass those probes.

