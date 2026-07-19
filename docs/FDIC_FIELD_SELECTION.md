# Phase 0 FDIC Field Selection

## Decision

The minimum viable Phase 1 financial request contains 50 fields across identity/peer grouping, capital, asset quality, earnings, funding/liquidity, and loan concentration. It is deliberately compact relative to the 2,378 properties in the financial API definition.

The supplied 2026 Q1 sample contains 41 of the 50 candidates. Missing from the sample but required for the historical design are:

`LNLSGR`, `OTHBFHLB`, `LNRECONS`, `LNREMULT`, `LNRERES`, `LNCI`, `LNCON`, `LNCRCD`, and `LNAG`.

## Selection by domain

| Domain | Count | Fields |
|---|---:|---|
| Identity, status, peers, scale | 10 | `CERT`, `RSSDID`, `NAMEFULL`, `REPDTE`, `STALP`, `BKCLASS`, `REGAGNT`, `ACTIVE`, `CB`, `ASSET` |
| Capital | 7 | `EQ`, `EQTOT`, `EQV`, `RBC1AAJ`, `IDT1CER`, `IDT1RWAJR`, `RBCRWAJ` |
| Asset quality | 7 | `LNLSGR`, `LNLSNET`, `P3ASSET`, `P9ASSET`, `NAASSET`, `NTLNLS`, `ORE` |
| Earnings | 9 | `NETINC`, `INTINC`, `EINTEXP`, `NONII`, `NONIX`, `PTAXNETINC`, `ROA`, `NIMY`, `EEFFR` |
| Funding and liquidity | 10 | `CHBAL`, `SC`, `DEP`, `DEPDOM`, `DEPUNINS`, `DEPCSBQ`, `COREDEP`, `FREPO`, `OTHBFHLB`, `INTEXPY` |
| Loan concentration | 7 | `LNRECONS`, `LNREMULT`, `LNRERES`, `LNCI`, `LNCON`, `LNCRCD`, `LNAG` |

## Historical availability tiers

These tiers are hypotheses from the definitions, not a frozen feature contract:

- **Broad-history candidates:** core identity, assets, equity, loans, delinquencies/nonaccrual, deposits, basic income/expense, cash, securities, and major loan categories. Phase 1 must verify exact quarter coverage from 2001 Q1.
- **Known regime breaks:** `IDT1CER` begins in 2014; risk-based ratios change with Basel III and CBLR; `LNRERES` subcategories change before 2004; `LNCRCD` changes around 2001; `DEPUNINS` thresholds and filing populations change in 2002, 2006, 2009, and 2019; `OTHBFHLB` is limited for some reporters before 2001.
- **Derived ratios:** `EQV`, `ROA`, `NIMY`, `EEFFR`, capital ratios, and `INTEXPY` are retained for reconciliation, while transparent SQL will recompute feasible ratios from underlying amounts.

## Exclusions

- Names, closing dates, acquirer names, and post-failure attributes are excluded from predictors.
- Sparse securitization balances in the sample are not selected merely because they are available.
- No attempt is made to download every Call Report variable.
- CET1 is not backfilled before it exists.
- Missing uninsured deposits are not fabricated for institutions outside the reporting population.

## Phase 1 acceptance test

For anchor quarters 2001 Q1, 2004 Q1, 2009 Q1, 2014 Q1, 2020 Q1, and the latest consistently completed quarter, Phase 1 must record:

1. HTTP response and metadata totals.
2. Returned fields and inferred types.
3. Row count and unique `CERT` count.
4. Per-field missingness and zero share.
5. Definition/regime notes.
6. Exact duplicate and duplicate bank-quarter counts.
7. Fields absent from the payload despite being requested.

Only after this table is reviewed may the historical field contract be frozen.

