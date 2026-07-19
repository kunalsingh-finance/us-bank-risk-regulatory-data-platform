# Phase 3 Risk-Feature Readiness

## Verdict

**Approved with documented exclusions.**

The canonical bank-quarter table is valid and safe for controlled Phase 3 ratio construction. Phase 3 must retain denominator guards, missingness flags, point-in-time discipline, and the failure/assistance distinction below.

## Readiness answers

1. **Canonical table:** Valid. `core.bank_quarter_financials` has exactly one row per CERT and quarter-end reporting date.
2. **Core rows:** 698,804.
3. **Historical institutions:** 11,073 distinct financial CERTs. The current institution dimension contains 27,836 unique CERTs.
4. **Identifier matching:** 11,067 of 11,073 financial CERTs match the current institution file (99.9458%); 10,856 match history events (98.0403%).
5. **Unmatched institutions:** Six financial CERTs are absent from the current-state institution reference. They remain in the fact. The history universe also contains 19,930 CERTs without panel financials because it includes pre-2001, branch, and non-reporting records.
6. **Failure matching:** 584 of 592 source references match panel financials (98.6486%). By source semantics, 571 of 579 `FAILURE` records and all 13 `ASSISTANCE` records match. The eight unmatched records are retained and left-censored.
7. **History matching:** 10,856 of 11,073 panel CERTs have history evidence. Of 352,107 history rows, 341,355 have a canonical CERT; 10,752 unresolved rows are almost entirely branch/acquisition records.
8. **Exceptions:** Critical 0; High 0; Medium 655; Low 236; Informational 13,697. Medium/Low financial exceptions are preserved source values, not rejected rows.
9. **Identifier conflicts:** No concurrent RSSDID-to-multiple-CERT overlap. Fifty-six RSSDIDs have non-overlapping sequential CERT mappings; 78 CERTs have multiple historical RSSDIDs. CERT plus reporting date remains the key.
10. **Source-definition conflicts:** Phase 1 resolutions remain binding. The failure reference contains both 579 failures and 13 assistance transactions, which must never be combined as failures.
11. **Ratio safety:** The approved financial fields are safe for controlled construction; no ratio was built in Phase 2.
12. **Denominator protections:** Require non-null, economically valid denominators for assets, equity, loans, deposits, and earning-asset-based measures. Zero or negative denominators must produce null plus an exception/flag, never infinity or a fabricated zero.
13. **Structural missingness:** Examples across the fact are equity 1,025 rows; assessable deposits 183; quarterly NIM 1,123; quarterly funding cost 1,123. Missingness must be profiled by quarter and not imputed automatically.
14. **Year caveats:** Retain the Phase 1 accounting/regulatory caveats, including the 2009 total-equity accounting change, regulator/OTS transition, and any quarter-level missingness documented in the continuity assessment. Current institution attributes are not point-in-time historical attributes.
15. **May Phase 3 begin?** Yes, with the exclusions below.

## Required Phase 3 exclusions and controls

- Use `resolution_type='FAILURE'` only when later designing failure labels; exclude `ASSISTANCE` from failure outcomes.
- Do not infer labels from mergers, acquisitions, inactive status, or unresolved branch events.
- Do not use the current institution file as if its attributes applied historically.
- Exclude unresolved history rows from institution-level joins unless a later evidence-based crosswalk resolves them.
- Preserve the six unmatched financial CERTs and all financial plausibility exceptions.
- Implement denominator guards and explicit missingness policy before any ratio is approved.
