# Phase 2 SQL Model Readiness

## Final verdict

**Approved for Phase 2 SQL data modelling.**

This approval covers loading the frozen ingestion-stage panel into DuckDB and designing typed, controlled SQL models. It does not pre-approve risk ratios, failure labels, macroeconomic joins, or modelling choices; those remain subject to their own gates.

## Readiness answers

1. **Exact quarters downloaded**  
   All 101 quarter ends from 2001 Q1 through 2026 Q1, inclusive. There are no gaps.

2. **Total bank-quarter rows**  
   698,804.

3. **Unique institutions**  
   11,073 unique `CERT` values.

4. **Earliest and latest reporting dates**  
   2001-03-31 and 2026-03-31.

5. **Core fields retained**  
   All 40 ordered fields in `configs/selected_financial_fields_v1.yaml`. The combined panel adds 11 ingestion-lineage fields and no analytical features.

6. **Fields with meaningful historical missingness**  
   None falls below 99% non-null in any quarter. Small persistent reporter-level gaps remain in several calculated quarterly ratios and selected balances, with the minimum at 99.7650%. Phase 2 must preserve these nulls and document any later treatment.

7. **Quarters with warnings**  
   None. All 101 quarters received `PASS`. One page in 2020 Q2 retried successfully and does not represent a data warning.

8. **Unresolved schema drift**  
   None. The schema-drift report contains zero events.

9. **Unresolved identifier issues**  
   None. `CERT`, `RSSDID`, and `REPDTE` are populated throughout the panel.

10. **Combined bank-quarter uniqueness**  
    Passed. There are zero duplicate (`CERT`, `REPDTE`) keys.

11. **Source lineage completeness**  
    Passed. Every combined row carries run, endpoint, quarter, page-count, manifest-path, timestamp, downloader-version, configuration-hash, quarter-raw-hash, normalization-version, and validation-status lineage.

12. **Safe to load into DuckDB**  
    Yes. The 54.36 MB Parquet is internally reconciled, hash-frozen, schema-stable, complete by quarter, and unique by bank-quarter.

13. **May Phase 2 begin?**  
    Yes, for SQL data modelling only.

14. **Required Phase 2 caveats**

    - Cast source-text financial columns explicitly in SQL and fail on invalid values; do not rely on permissive implicit casts.
    - Preserve source nulls. Any imputation requires a later, separately reviewed analytical decision.
    - Treat the approved FDIC population filter as part of dataset lineage.
    - Retain `CERT` as the primary identifier and `RSSDID` as a secondary identifier.
    - Carry forward the small historical missingness documented in the validation report.
    - Investigate small-base distribution changes before defining outlier controls; do not automatically remove them.
    - Continue excluding Phase 1 Conditional, Replace, and Derived fields unless a separately versioned supplemental ingestion is approved.
    - Do not call later public-data indicators official CAMELS ratings.

## Approved Phase 2 source

```text
data/processed/ingestion_stage/fdic_financials_2001q1_2026q1.parquet
```

SHA-256:

```text
94d360d8e39c86658350e5b981d389e0d4c3c48376dc89adaa223caf6ef0232c
```
