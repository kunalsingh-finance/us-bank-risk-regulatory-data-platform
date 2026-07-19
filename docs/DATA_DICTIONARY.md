# Preliminary Data Dictionary

## Conventions

- Monetary FDIC financial values are reported in **thousands of U.S. dollars** unless a definition states otherwise.
- Percentage values are stored as percentage points in the source and will be normalized explicitly in staging.
- `YTD` income/expense amounts require quarter-aware conversion when a standalone-quarter flow is needed.
- “Sample” indicates presence in the supplied 2026 Q1 file, not historical continuity.
- Availability remains provisional until Phase 1 anchor-quarter probes are complete.

## Candidate financial fields

| Domain | FDIC code | Meaning | Unit / frequency | In sample | Intended use or denominator | Material caveat |
|---|---|---|---|---|---|---|
| Identity | `CERT` | FDIC certificate number | Identifier / quarterly | Yes | Primary bank key | Track certificate changes via history events |
| Identity | `RSSDID` | Federal Reserve entity ID | Identifier / quarterly | Yes | Secondary identifier | Definition narrative mentions top-holder context; retain source value exactly |
| Identity | `NAMEFULL` | Name at report date | Text / quarterly | Yes | Display only | Never use name text as a predictor or sole join key |
| Identity | `REPDTE` | Report date | Date / quarterly | Yes | Bank-quarter key | Must be valid quarter end |
| Peer | `STALP` | Main-office state | Code / quarterly | Yes | Geographic peer attribute | State changes require history reconciliation |
| Peer | `BKCLASS` | Charter/regulatory class | Code / quarterly | Yes | Peer grouping | Meaning can change after charter conversion |
| Peer | `REGAGNT` | Primary federal regulator | Code / quarterly | Yes | Governance/peer attribute | OTS ceased in 2011; preserve historical codes |
| Status | `ACTIVE` | Active insured status | Flag / quarterly | Yes | Population control | Inactive does not mean failed |
| Peer | `CB` | FDIC community-bank flag | Flag / quarterly | Yes | Business-model proxy | Definition and size thresholds evolve; 9 sample values missing |
| Scale | `ASSET` | Total assets | $000 / quarter end | Yes | Size and most asset ratios | Excludes off-balance-sheet items |
| Capital | `EQ` | Bank equity capital | $000 / quarter end | Yes | `equity_to_assets` numerator | 9 sample values missing |
| Capital | `EQTOT` | Consolidated total equity | $000 / quarter end | Yes | Consolidated capital cross-check | Minority-interest treatment changed in 2009 |
| Capital | `EQV` | Equity capital / assets | % / quarterly | Yes | Source ratio cross-check | Workbook narrative is wrong; recompute from `EQ / ASSET` |
| Capital | `RBC1AAJ` | Tier 1 leverage ratio | % / quarterly | Yes | Capital indicator | CBLR framework affects interpretation after 2020 |
| Capital | `IDT1CER` | CET1 risk-based capital ratio | % / quarterly | Yes | CET1 indicator | Available from 2014; often unavailable for CBLR electors after 2020 |
| Capital | `IDT1RWAJR` | Tier 1 risk-based capital ratio | % / quarterly | Yes | Tier 1 indicator | Basel III/CBLR comparability breaks |
| Capital | `RBCRWAJ` | Total risk-based capital ratio | % / quarterly | Yes | Total capital indicator | Not available for some CBLR electors |
| Asset quality | `LNLSGR` | Gross loans and leases, net of unearned income | $000 / quarter end | No | Loan denominator | Must be added to Phase 1 query |
| Asset quality | `LNLSNET` | Net loans and leases | $000 / quarter end | Yes | Balance-sheet cross-check | Net of allowance; not the preferred delinquency denominator |
| Asset quality | `P3ASSET` | Assets 30–89 days past due | $000 / quarter end | Yes | Early delinquency numerator | Institution-level reporting has confidentiality caveats in definition |
| Asset quality | `P9ASSET` | Assets 90+ days past due and accruing | $000 / quarter end | Yes | Severe delinquency numerator | Includes assets beyond loans |
| Asset quality | `NAASSET` | Nonaccrual assets | $000 / quarter end | Yes | Nonaccrual numerator | Includes non-loan assets |
| Asset quality | `NTLNLS` | Net loan and lease charge-offs | $000 / YTD | Yes | Charge-off ratio numerator | Convert YTD flows without future data; 9 sample values missing |
| Asset quality | `ORE` | Other real estate owned | $000 / quarter end | Yes | Distressed-asset indicator | Net of valuation allowances; 9 sample values missing |
| Earnings | `NETINC` | Net income attributable to bank | $000 / YTD | Yes | ROA/earnings trend | Convert YTD to quarter flow; 9 sample values missing |
| Earnings | `INTINC` | Total interest income | $000 / YTD | Yes | Revenue/funding diagnostics | Convert YTD to quarter flow |
| Earnings | `EINTEXP` | Total interest expense | $000 / YTD | Yes | Funding-cost diagnostics | Convert YTD to quarter flow |
| Earnings | `NONII` | Noninterest income | $000 / YTD | Yes | Revenue mix | Convert YTD to quarter flow |
| Earnings | `NONIX` | Noninterest expense | $000 / YTD | Yes | Efficiency and operating cost | Convert YTD to quarter flow |
| Earnings | `PTAXNETINC` | Pretax net operating income | $000 / YTD | Yes | Pre-provision/profitability basis | Definition is terse; reconcile components |
| Earnings | `ROA` | Return on assets | % / annualized YTD | Yes | Profitability indicator | Prefer recomputed check where average assets are available |
| Earnings | `NIMY` | Net interest margin | % / annualized YTD | Yes | Margin indicator | Use `NIMY`, not ambiguous `NIM` |
| Earnings | `EEFFR` | Efficiency ratio | % / annualized YTD | Yes | Operating-efficiency indicator | Lower is generally better; definition excludes some intangible amortization |
| Liquidity | `CHBAL` | Cash and balances due | $000 / quarter end | Yes | Liquid-assets numerator | Includes interest- and noninterest-bearing balances |
| Liquidity | `SC` | Total securities | $000 / quarter end | Yes | Liquid-assets proxy | Accounting and CECL treatment changes over time |
| Funding | `DEP` | Total deposits | $000 / quarter end | Yes | Deposit and loan/deposit denominator | Includes foreign-office deposits |
| Funding | `DEPDOM` | Domestic deposits | $000 / quarter end | Yes | Domestic funding denominator | Workbook note incorrectly says “as of June 30”; verify quarterly behavior |
| Funding | `DEPUNINS` | Estimated uninsured deposits | $000 / quarter end | Yes | Uninsured-deposit ratio | Reporting thresholds and definitions change; workbook definition is blank |
| Funding | `DEPCSBQ` | Estimated assessable deposits | $000 / average quarter | Yes | Assessment-base diagnostic | Estimate may differ from official assessment statement |
| Funding | `COREDEP` | Core retail deposits | $000 / quarter end | Yes | Stable-funding ratio | 9 sample values missing; definition evolves |
| Liquidity | `FREPO` | Fed funds sold and reverse repos | $000 / quarter end | Yes | Liquid-assets proxy | TFR definition differs before 1998 |
| Funding | `OTHBFHLB` | FHLB advances | $000 / quarter end | No | Wholesale-funding ratio | Pre-2001 availability limited for non-TFR reporters |
| Funding | `INTEXPY` | Cost of funding earning assets | % / annualized YTD | Yes | Funding-cost indicator | Denominator is average earning assets, not total funding |
| Concentration | `LNRECONS` | Construction and land-development loans | $000 / quarter end | No | Loans / `LNLSGR` | Add to Phase 1 query |
| Concentration | `LNREMULT` | Multifamily real-estate loans | $000 / quarter end | No | Loans / `LNLSGR` | Add to Phase 1 query |
| Concentration | `LNRERES` | 1–4 family residential real-estate loans | $000 / quarter end | No | Loans / `LNLSGR` | Subcategory reporting differs before 2004 |
| Concentration | `LNCI` | Commercial and industrial loans | $000 / quarter end | No | Loans / `LNLSGR` | Add to Phase 1 query |
| Concentration | `LNCON` | Consumer loans to individuals | $000 / quarter end | No | Loans / `LNLSGR` | Includes credit cards and other consumer loans |
| Concentration | `LNCRCD` | Credit-card loans | $000 / quarter end | No | Loans / `LNLSGR` | Definition changed around 2001 |
| Concentration | `LNAG` | Agricultural production loans | $000 / quarter end | No | Loans / `LNLSGR` | Excludes some former TFR reporters |

## Event and failure fields

| Dataset | Fields | Use | Control |
|---|---|---|---|
| Failures | `CERT`, `FIN`, `FAILDATE`, `FAILYR`, `NAME`, `RESTYPE`, `RESTYPE1`, `QBFASSET`, `QBFDEP` | Confirm FDIC failure, close date, resolution context, and prior reported scale | Require valid `CERT` and parsed date; never use failure outcome fields as predictors |
| History | `ID`, `CERT`, `TRANSNUM`, `UNINUM`, `EFFDATE`, `PROCDATE`, `CHANGECODE`, `CHANGECODE_DESC`, event flags | Classify structure events and exits | Event `ID` unique; do not assume `TRANSNUM` or `CERT` uniqueness |
| History counterparties | `SUR_CERT`, `OUT_CERT`, `ACQ_CERT`, related `UNINUM` fields | Trace survivors, outgoing entities, and acquirers | Preserve directed roles; never classify acquisition alone as failure |

