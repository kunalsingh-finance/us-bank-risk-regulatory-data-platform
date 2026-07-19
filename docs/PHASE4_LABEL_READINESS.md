# Phase 4 Label Readiness

## Verdict

**Approved with documented feature exclusions.**

1. Every canonical bank-quarter has one feature row: 698,804 of 698,804, with a unique CERT-reporting-date key.
2. Sixty-five features were created across seven risk families.
3. Modelling candidates include protected continuous capital, asset-quality, earnings, liquidity/funding, concentration and growth measures, their leakage-free trends, and peer-relative values when `peer_count >= 20` and row-level quality flags pass.
4. Descriptive-only features include assessable-deposit share, reported real-estate/business-mix shares, loan-category coverage, non-monotonic concentration shares, and screening flags. They require separate model-risk approval before predictive use.
5. No conditional source field was built. Time-dependent features are conditional on exact lag/rolling history. `DEPUNINS` and regulatory-capital fields remain excluded.
6. No feature exceeds 12% missingness. The highest missingness is expected history insufficiency: noncurrent slope/volatility 11.476%; four other eight-quarter measures 10.901%.
7. Denominator evidence includes 12,082 missing, 5,588 zero, and 289 negative denominators, plus 11,073 initial insufficient-lag events. Affected features remain null.
8. Non-monotonic/descriptive measures do not receive risk-adjusted percentiles unless an explicit transformation is later approved.
9. Temporal calculations are leakage-free: zero future prior dates; 687,731 exact one-quarter and 655,157 exact year-ago matches.
10. All peer calculations are same-quarter. Peer IDs include the reporting date.
11. Detailed and broad fallback rules work, but 93,890 of 18,393,982 benchmark rows still have fewer than 20 non-null broad peers. Exclude those peer-relative values from modelling.
12. Raw and peer-relative outputs are logically reproducible: consecutive builds had identical feature/peer row counts and all 12 identical report hashes.
13. Quality flags are complete and separate: numerator, denominator, lag, rolling, conditional availability, peer size, extreme, unit, identifier and source warnings.
14. Later modelling must exclude first-history lag gaps, the first seven observations for eight-quarter features, peer rows below 20, unsupported Core-v1 candidates, invalid denominators, and source/identifier warning rows according to a documented policy. The calendar year alone is not a sufficient exclusion rule because banks enter throughout the sample.
15. Phase 4 failure and deterioration label construction may begin under these exclusions. It must use only `resolution_type='FAILURE'`, never assistance, merger, acquisition, inactive status, or a feature-derived screening flag as a failure label.

No label was created in Phase 3.
