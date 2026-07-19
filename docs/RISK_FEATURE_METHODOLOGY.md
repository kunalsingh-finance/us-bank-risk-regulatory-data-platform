# Risk Feature Methodology

Phase 3 converts the approved 40-field bank-quarter fact into 65 transparent **public-data CAMELS-style risk indicators**. They are not official CAMELS ratings, supervisory findings, failure probabilities, or causal estimates.

The Phase 2 database is attached read-only and hash-verified. A separate, git-ignored Phase 3 database copies the canonical fact unchanged, calculates feature families in ordered SQL, reconciles one feature row and one quality row to every bank-quarter, creates same-quarter peers, and writes long-form peer benchmarks. Python orchestrates the transaction, configuration/SQL hashes, validation, and deterministic report exports.

## Feature families

| Family | Features | Approach |
|---|---:|---|
| Capital | 8 | Accounting equity/assets, balance and ratio changes, trailing slope/volatility, screening flag |
| Asset quality | 10 | Past-due/nonaccrual public-data proxies, charge-offs on average loans, trends and flags |
| Earnings | 13 | Source quarterly ROA/NIM/efficiency, derived flow ratios, changes, rolling history and losses |
| Liquidity | 3 | Liquid-assets proxy, loan/deposit pressure, deterioration flag |
| Funding | 10 | Deposit reliance/growth/outflow proxy, FHLB reliance, source funding cost and flags |
| Concentration | 12 | Six non-overlapping reported categories, coverage, incomplete-portfolio HHI and change |
| Growth | 9 | Quarterly/yearly asset and loan growth, capital growth and loan/deposit funding gaps |

Thirteen requested features were excluded because Core-v1 intentionally omitted regulatory-capital ratios, allowances, provisions, brokered/uninsured deposits, broader borrowings, or agricultural loans. `DEPUNINS` remains conditional and is not used.

Temporal calculations use exact one- and four-quarter prior dates. Eight-quarter windows use only the current and seven preceding rows, require eight valid observations, and never use centered windows. Current/prior average balances are used only when both observations are valid. Extreme values are preserved with flags; no winsorization, truncation, or imputation occurs.

Screening flags use documented thresholds and remain separate from raw measures. They are recruiter-visible diagnostics, not composite scores. Failure and assistance tables are not joined into feature calculations.
