# Feature Denominator Policy

Every Phase 3 derived ratio uses an explicit `CASE WHEN denominator > 0 THEN ... END` pattern. A null, zero, or economically invalid negative denominator produces a null feature and a traceable exception; it never produces zero, infinity, or an imputed value.

| Denominator family | Valid condition | Features affected | Invalid treatment |
|---|---|---|---|
| Total assets | non-null and positive | capital, liquidity, funding and asset-growth ratios | Null feature; `MISSING`, `ZERO`, or `NEGATIVE_DENOMINATOR` |
| Gross loans | non-null and positive | asset-quality and concentration ratios | Null feature and loan-family exception |
| Deposits | non-null and positive | loans/deposits and deposit composition | Null feature and deposit-family exception |
| Average assets | current and exact prior-quarter assets positive; average positive | income/expense ratios | Null until valid prior history; no future balance |
| Average loans | current and exact prior-quarter gross loans positive; average positive | annualized quarterly charge-off ratio | Null until valid prior history |
| Average equity | current and exact prior-quarter equity positive; average positive | return on equity | Null for missing, zero, or negative average equity |
| Prior balance for growth | exact prior/year-ago balance exists and absolute value is positive | percentage growth | Null and continuity/denominator flag |
| Covered category balance | at least one available positive reported category | loan HHI | Null HHI; coverage remains explicit |

Quarterly flow ratios multiply by 400 to express an annualized percentage only when the numerator is a single-quarter dollar flow and the denominator is a valid average balance. Source-reported `ROAQ`, `NIMYQ`, and `INTEXPYQ` are already annualized quarterly ratios and are preserved without another annualization.

Phase 3 recorded 11,073 insufficient-lag denominator events, 12,082 missing denominators, 5,588 zero denominators, and 289 negative denominators. These are availability evidence, not source-row exclusions.
