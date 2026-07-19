# Field Definition Resolution

## Decision summary

The Phase 1 probes resolve the three Phase 0 definition conflicts and one related capital-regime issue:

- `EQV` is an FDIC-calculated equity-to-assets ratio, not an equity balance. It is exactly reproducible from `100 × EQ / ASSET` and is classified **Derived** rather than retained in the core API query.
- `NIM` is YTD net interest income in USD thousands; `NIMQ` is its quarterly counterpart. `NIMY` is annualized YTD net interest margin; `NIMYQ` is the quarterly margin and is rounded to two decimals. `NIMY` is classified **Replace** and `NIMYQ` is approved as **Core**.
- `DEPUNINS` and `DEPUNA` are not interchangeable. Both have similar titles, but they differ for most institutions. `DEPUNINS` is classified **Conditional** and excluded from the baseline model and core historical query.
- `CBLRIND` is required whenever post-2020 risk-based capital ratios are requested because zero-filled ratios for CBLR electors mean “not required/not available,” not zero regulatory capital.

## Evidence table

| Field | Official definition | Source file and location | Units | Validated availability | Interpretation | Conflict | Resolution | Final decision | Caveat |
|---|---|---|---|---|---|---|---|---|---|
| `EQV` | Bank equity capital divided by total assets | `fdic_financial_api_definitions.yaml`, YAML line 8,297; workbook `Reference-Variables&Definitions`, row 531 | Percent | All six anchors | FDIC-calculated ratio using `EQ / ASSET` | Workbook row 531 incorrectly contains the uninsured-deposit narrative | 38,026 comparable rows across the anchors matched `100 × EQ / ASSET`; maximum absolute difference was `1.42e-14` | **Derived** | Calculate in SQL from `EQ` and `ASSET`; use source `EQV` only for reconciliation |
| `NIM` | Net interest income: total interest income less total interest expense | YAML line 3,584; workbook row 1,253 | USD thousands, YTD | At least 99.8% populated in every anchor definition probe | Cumulative current-year dollar flow | Similar name to margin fields | `NIM = INTINC - EINTEXP` exactly after 2001; 9 of 9,822 comparable 2001 rows differed by at most USD 9 thousand | Not selected; use `NIMQ` | Never treat Q2–Q4 `NIM` as a single-quarter flow |
| `NIMQ` | Quarterly net interest income | YAML line 3,603; workbook row 1,256 | USD thousands, quarterly | At least 99.8% in every anchor | Single-quarter dollar flow | Missing from Phase 0 list | Validated on all six anchors; equals `NIM` in Q1 and differs in later quarters as expected | **Core** | Source value remains subject to source revisions |
| `NIMY` | Annualized YTD net interest income divided by average earning assets | YAML line 12,631; workbook row 1,259 | Percent, annualized YTD | 100% non-null in every anchor | YTD margin | Could be mistaken for quarterly margin | Exact match to `100 × NIMA / ERNAST5` in every comparable anchor row | **Replace** | Replace with `NIMYQ` for the bank-quarter panel |
| `NIMYQ` | Quarterly net interest margin | YAML line 12,643; workbook row 1,260 | Percent, quarterly | At least 99.8% in every anchor | Single-quarter annualized margin | Not in Phase 0 list | Validated on all anchors; Q1 values reconcile to `NIMY` within 0.005 percentage points because `NIMYQ` is rounded to two decimals | **Core** | Preserve source rounding and flag extreme denominators |
| `DEPUNINS` | Estimated uninsured deposits in domestic offices and insured U.S.-territory branches | YAML line 6,777; workbook has no populated definition row | USD thousands, quarter end | Non-null for 100% of every anchor | FDIC API estimate/source field | Definition narrative is absent and it was assumed potentially equivalent to `DEPUNA` | Not equivalent: exact for only 1,260/9,838 institutions in 2001 Q1 and 1,025/4,287 in 2026 Q1 | **Conditional** | Exclude from baseline model and core query until estimation methodology is documented |
| `DEPUNA` | Reported estimated uninsured deposits for the applicable filing population | YAML line 6,758; workbook row 297 | USD thousands, quarter end | Non-null 8,016/8,314 in 2008 Q4 and complete in most other anchors, but often zero | Reported filing item with size/form changes | Similar title to `DEPUNINS` | Retained only as a reporting-population control | **Conditional** | Zero often means no reported amount, not no uninsured deposits; reporting thresholds changed in 2002, 2006, 2009, and 2019 |
| `CBLRIND` | Flag equal to 1 when the institution elected the CBLR framework | YAML line 91; workbook row 67 | Flag | Not applicable before 2020; 1,846 electors in 2020 Q2, 1,664 in 2023 Q1, and 1,732 in 2026 Q1 | Capital-regime control | Risk-based ratios appear as zero rather than null for electors | Mandatory companion for conditional capital-ratio analysis | **Conditional** | Excluded from the core query because the conditional capital ratios are excluded |
| `IDT1CER` | CET1 capital divided by risk-weighted assets for non-CBLR institutions | YAML line 20,639; workbook row 683 | Percent | Officially begins March 2014; 100% zero in 2001, 2008, and 2012 anchors | Regulatory capital ratio | API zero-fills unavailable periods and CBLR electors | Treat pre-2014 and CBLR zeros as unavailable | **Conditional** | Earliest nonzero anchor evidence is 2020 Q2; not approved for the core query |
| `IDT1RWAJR`, `RBCRWAJ` | Tier 1 and total risk-based capital ratios | YAML lines 20,651 and 16,743; workbook rows 684 and 1,793 | Percent | Present in all anchors; approximately 36%–41% zero after 2020 | Regulatory capital ratios | Zero is ambiguous without CBLR status; extreme ratios occur with small denominators | Use only in a regime-aware supplemental dataset | **Conditional** | Basel III and CBLR create structural breaks |

## Quarterly replacement decisions

The following Phase 0 YTD fields are replaced in the approved core query:

| Phase 0 field | Problem | Approved quarterly replacement |
|---|---|---|
| `NTLNLS` | YTD charge-offs | `NTLNLSQ` |
| `NETINC` | YTD net income | `NETINCQ` |
| `NONII` | YTD noninterest income | `NONIIQ` |
| `NONIX` | YTD noninterest expense | `NONIXQ` |
| `PTAXNETINC` | YTD pretax income | `PTAXNETINCQ` |
| `ROA` | Annualized YTD ratio | `ROAQ` |
| `NIMY` | Annualized YTD margin | `NIMYQ` |
| `EEFFR` | YTD efficiency ratio | `EEFFQR` |
| `INTEXPY` | Annualized YTD funding-cost ratio | `INTEXPYQ` |

`INTINC` and `EINTEXP` remain conditional YTD fields because no selected direct quarterly dollar counterparts were validated. If ever used, quarter flows must be produced with same-bank, same-year lag differencing and explicit Q1 logic; they are excluded from the core query.

## Source hierarchy

When definition assets conflict, the decision hierarchy is:

1. FDIC YAML formula/source mapping.
2. Live API behavior across approved anchors.
3. FDIC workbook title and narrative.
4. Manual sample reconciliation.

No similarly named fields are assumed equivalent without the live comparison recorded in `reports/field_definition_probe.csv`.

