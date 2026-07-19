# Full Historical Extraction Validation

## Validation conclusion

The complete Core-v1 archive passed the Phase 1B ingestion controls.

- Expected and completed quarters: **101 / 101**
- Coverage: **2001 Q1 through 2026 Q1**
- Total bank-quarter rows: **698,804**
- Unique `CERT` values: **11,073**
- API pages: **747**
- Quarter results: **101 PASS, 0 PASS_WITH_WARNINGS, 0 failed**
- Duplicate `CERT`-`REPDTE` keys: **0**
- Missing `CERT`, `RSSDID`, or `REPDTE`: **0**
- Schema drift events: **0**
- Extraction exceptions: **0**
- Combined Parquet SHA-256: `94d360d8e39c86658350e5b981d389e0d4c3c48376dc89adaa223caf6ef0232c`

## Pagination, retries, and hashes

All 747 page manifests reconcile to 698,804 rows and every raw-page hash verifies. One page—2020 Q2 at offset 4,000—required a second attempt after a transient request failure. The retry succeeded within policy, and that quarter passed all controls. There were no exhausted retries or failed quarters.

For every quarter, the combined raw JSONL, source-normalized CSV, and lineage-normalized CSV hashes match the completion marker. The combined Parquet row count equals the approved quarter total exactly.

## Identifier and uniqueness controls

Every row has a parseable `CERT`, a populated `RSSDID`, and the requested quarter-end `REPDTE`. The key (`CERT`, `REPDTE`) is unique within every quarter and across the combined panel.

The dataset contains 11,073 distinct `CERT` values over the full history. Institution counts decline from 9,838 in 2001 Q1 to 4,287 in 2026 Q1. The largest quarter-over-quarter decline is approximately 1.54% in 2019 Q4, well below the 10% discontinuity threshold. No sudden population increase or missing quarter was observed.

## Missingness continuity

No Core field falls below 99% non-null in any quarter, and no Core field is entirely null.

The lowest observed non-null rates are:

| Field group | Minimum non-null rate | Interpretation |
|---|---:|---|
| `NIMYQ`, `INTEXPYQ` | 99.7650% | Small source-level ratio unavailability; preserved as null |
| `EEFFQR` | 99.7731% | Small calculated-ratio unavailability; preserved as null |
| `NIMQ`, `EQTOT`, `LNCRCD`, `OTHBFHLB`, `ORE`, `LNCON`, `EQ`, `NTLNLSQ`, `ROAQ`, `NONIXQ`, `NETINCQ`, `NONIIQ` | 99.7901% | Small reporter-level gaps; no imputation |
| `LNREMULT`, `LNRECONS`, `LNRERES` | 99.8303% | Limited historical reporter gaps in 30 quarters |
| `DEPCSBQ` | 99.8303% | Limited gaps in 12 quarters |

All other Core fields are fully populated in every quarter. These small gaps are source missingness, not extraction failures, and should remain explicit in Phase 2.

## Distribution and structural-break review

No evidence of a unit change or unexplained schema break was found. The largest median fold changes were reviewed rather than removed:

- `NTLNLSQ`: median 15 to 1 from 2014 Q4 to 2015 Q1; a small-base quarterly flow and Q4-to-Q1 seasonal comparison, not a unit change.
- `ORE`: median 20 to 2.5 from 2020 Q1 to Q2, with roughly half the population at zero; a small-base shift, not a schema change.
- `OTHBFHLB`: median 670.5 to 99.5 from 2020 Q4 to 2021 Q1, again with a near-50% zero share.
- `FREPO`: median 305 to 100 from 2011 Q1 to Q2 with a high zero share.
- `P9ASSET`: median 1 to 3 from 2012 Q2 to Q3; the apparent fold change is driven by a very small median.

These values are retained unchanged. They are continuity caveats for later analytical design, not grounds for deleting quarters or altering source values.

## Immutable evidence

The independent audit reverified:

- 11 of 11 Phase 0 source hashes with zero failures
- 43 of 43 Phase 1 anchor-response page hashes with zero failures
- 747 of 747 Phase 1B page hashes with zero failures
- 101 of 101 quarter completion markers and final-file hashes

The Core-v1 archive was written beside, not over, the earlier anchor evidence.

## Resume and idempotency

A clean post-completion rerun skipped all 101 completed quarters, issued no API requests, revalidated the stored manifests and hashes, and reproduced the same combined Parquet hash. The rerun completed in approximately 17 seconds.

## Restrictions confirmed

- Financial values imputed: **No**
- Risk ratios calculated: **No**
- Lags calculated: **No**
- Failure labels created: **No**
- Failure/history/macro data merged: **No**
- SQL analytical model built: **No**
- Predictive model trained: **No**
