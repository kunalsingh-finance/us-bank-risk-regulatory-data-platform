# Phase 1 Full-Download Readiness

## Final verdict

**Approved with conditional fields excluded.**

The full 2001 Q1–latest completed-quarter download may begin using only the 40-field core query frozen in `configs/selected_financial_fields_v1.yaml`. It must not include the 12 conditional fields unless a later, separately versioned supplemental query implements their regime-specific controls.

This verdict authorizes ingestion only. It does not authorize risk features, labels, modelling, macro data, or a dashboard.

## Readiness questions

1. **Which fields are approved as core?**  
   Forty fields: nine identity/peer/status/scale fields; `EQ`, `EQTOT`; six core asset-quality balances; seven funding/liquidity balances; six loan-concentration balances; and ten explicit quarterly earnings/charge-off fields. The exact ordered list is the `approved_core_query` in the selected-field configuration.

2. **Which fields are conditional?**  
   `CB`, `RBC1AAJ`, `IDT1CER`, `IDT1RWAJR`, `RBCRWAJ`, `INTINC`, `EINTEXP`, `DEPUNINS`, `COREDEP`, `LNAG`, `CBLRIND`, and `DEPUNA`.

3. **Which fields were removed?**  
   None were classified Remove. Nine were classified Replace and are excluded from the approved query: `NTLNLS`, `NETINC`, `NONII`, `NONIX`, `PTAXNETINC`, `ROA`, `NIMY`, `EEFFR`, and `INTEXPY`. `EQV` is excluded because it is Derived.

4. **Which fields remain unresolved?**  
   None block the core query. `DEPUNINS` methodology remains insufficient for baseline modelling, so it is controlled by exclusion rather than assumed resolved.

5. **Are `EQV`, `NIM`/`NIMY`, and `DEPUNINS` resolved?**  
   `EQV` and the NIM family are resolved. `DEPUNINS` is correctly classified Conditional and excluded because it is not equivalent to `DEPUNA` and its estimation methodology is not documented sufficiently for baseline modelling.

6. **Does API pagination work reliably?**  
   Yes. Forty-three anchor pages reconciled exactly to metadata totals with deterministic ordering and no duplicate page hashes.

7. **Does resume/checkpoint logic work?**  
   Yes. Automated tests verify interruption, restart from the next offset, idempotent rerun, and query-hash binding.

8. **Does the API reconcile with the manual sample?**  
   Yes. The 2026 Q1 population is 4,287 in both sources, and all values for all 41 shared requested fields matched exactly.

9. **Are anchor schemas sufficiently stable?**  
   Yes for the 40-field core query. All core source fields or their validated quarterly replacements are broadly available at every anchor. This does not waive quarter-by-quarter schema validation.

10. **Can the full historical download begin safely?**  
    Yes, for the approved 40-field core query only.

11. **What risks remain?**  
    Intervening-quarter schema changes, FDIC source revisions, accounting-rule changes, extreme denominator effects, and industry-population shifts. Conditional capital, uninsured-deposit, community-bank, core-deposit, and agricultural fields remain outside the core query.

12. **What is the approved final historical query?**

```text
CERT,RSSDID,NAMEFULL,REPDTE,STALP,BKCLASS,REGAGNT,ACTIVE,ASSET,
EQ,EQTOT,LNLSGR,LNLSNET,P3ASSET,P9ASSET,NAASSET,ORE,
CHBAL,SC,DEP,DEPDOM,DEPCSBQ,FREPO,OTHBFHLB,
LNRECONS,LNREMULT,LNRERES,LNCI,LNCON,LNCRCD,
NIMQ,NIMYQ,NETINCQ,NONIIQ,NONIXQ,PTAXNETINCQ,ROAQ,EEFFQR,INTEXPYQ,NTLNLSQ
```

Population filter:

```text
ACTIVE:1 AND !(BKCLASS:NC) AND REPDTE:<quarter-end YYYYMMDD>
```

13. **What row count and storage size should be expected?**  
    A linear population estimate from 9,838 institutions in 2001 Q1 to 4,287 in 2026 Q1 produces approximately **713,000 bank-quarter rows** through 2026 Q1. Based on observed anchor bytes per row and scaling from 50 to 40 fields, expect roughly **207 MB normalized CSV** and **463 MB raw JSON**, before manifests, checkpoints, and compression. A prudent capacity range is 0.7–1.0 GB.

14. **What happens if a historical quarter returns an incomplete schema?**  
    Stop that quarter and the run. Preserve accepted write-once pages, record an ingestion exception, compare the API metadata/definitions and adjacent quarters, and either correct the query under a new configuration version or reclassify the field. Never silently drop the field, coerce it, substitute a similarly named field, or continue with a partial quarter.

## Remaining gate

Phase 2 may not begin yet. The approved full core download must first be executed, reconciled for every quarter, and documented in a separate ingestion completion update.

