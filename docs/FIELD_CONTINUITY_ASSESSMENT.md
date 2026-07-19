# Field Continuity Assessment

## Scope

The assessment covers only the six preregistered anchors: 2001 Q1, 2008 Q4, 2012 Q4, 2020 Q2, 2023 Q1, and 2026 Q1. It does not prove that every intervening quarter is complete; the full downloader must still stop on a schema or population break.

## Anchor results

| Quarter | Rows | Pages | Unique CERT | Duplicate bank-quarter rows | Validation |
|---|---:|---:|---:|---:|---|
| 2001 Q1 | 9,838 | 10 | 9,838 | 0 | Pass |
| 2008 Q4 | 8,314 | 9 | 8,314 | 0 | Pass |
| 2012 Q4 | 7,092 | 8 | 7,092 | 0 | Pass |
| 2020 Q2 | 5,075 | 6 | 5,075 | 0 | Pass |
| 2023 Q1 | 4,681 | 5 | 4,681 | 0 | Pass |
| 2026 Q1 | 4,287 | 5 | 4,287 | 0 | Pass |

All 43 anchor pages reconciled to API metadata totals. Every row had `CERT`, `RSSDID`, and the expected `REPDTE`. `ID` was the only unrequested system field and is explicitly allowed by the schema contract.

## Nine fields absent from the manual sample

All nine fields were accepted by the API at every anchor:

| Field | 2001 Q1 non-null | 2008 Q4 non-null | 2012 Q4 onward | Decision |
|---|---:|---:|---|---|
| `LNLSGR` | 100.0% | 100.0% | 100.0% | Core |
| `OTHBFHLB` | 99.84% | 99.89% | At least 99.79% | Core |
| `LNRECONS` | 99.84% | 100.0% | 100.0% | Core |
| `LNREMULT` | 99.84% | 100.0% | 100.0% | Core |
| `LNRERES` | 99.84% | 100.0% | 100.0% | Core |
| `LNCI` | 100.0% | 100.0% | 100.0% | Core |
| `LNCON` | 99.84% | 99.89% | At least 99.79% | Core |
| `LNCRCD` | 99.84% | 99.89% | At least 99.79% | Core with documented 2001 definition caveat |
| `LNAG` | 89.06% | 90.15% | At least 99.79% | Conditional because early TFR reporting is incomplete |

The `field_probe_results.csv` report contains counts, percentages, distinct values, minimums, maximums, and recommendations for all 54 field-anchor combinations.

## Manual/API reconciliation

The 2026 Q1 API anchor and manual file both contain 4,287 institutions. For all 41 fields shared between the validated API request and the manual sample:

- CERT population matched exactly.
- Every compared value was an exact textual/numeric match.
- No rounding, timing, population, missing-field, or unresolved discrepancy was observed.

This is stronger than a row-count-only reconciliation, but it validates only the 2026 Q1 snapshot.

## Structural breaks and sentinel behavior

- `IDT1CER` is 100% zero in the 2001, 2008, and 2012 anchors although its official introduction is March 2014. Those zeros are unavailable sentinels.
- After CBLR adoption, 36%–41% of `IDT1CER`, `IDT1RWAJR`, and `RBCRWAJ` observations are zero. `CBLRIND` identifies most of those observations as not required/not available.
- `DEPUNINS` is non-null across all anchors but differs materially from `DEPUNA`; non-null coverage is not evidence of consistent methodology.
- `LNAG` has an early reporting-population gap associated with former TFR reporters.
- YTD income and ratio fields differ from their quarterly counterparts outside Q1, as expected.
- `EEFFR` and historical capital ratios contain extreme values caused by small/negative denominators. They are flagged, not automatically removed.
- Institution counts decline from 9,838 in 2001 Q1 to 4,287 in 2026 Q1. This is plausible industry consolidation and not treated as missing pages.

## Field contract result

All 50 Phase 0 candidates are classified:

- 30 remain Core.
- 10 are Conditional.
- 9 are replaced by validated quarterly counterparts.
- 1 (`EQV`) is Derived.

Ten validated quarterly replacements expand the final core query to 40 fields. Two additional conditional control fields, `CBLRIND` and `DEPUNA`, are documented but excluded from the core query. The complete contract is `configs/selected_financial_fields_v1.yaml`.

