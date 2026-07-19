# History Event Taxonomy

`core.institution_history_events` assigns one descriptive taxonomy to every source history row. The mapping is implemented in `sql/010_build_history_events.sql`; raw codes, descriptions, flags, predecessor/successor identifiers, and lineage remain on the row. This taxonomy is not an outcome label.

| Taxonomy | Official evidence used | Interpretation | Limitation |
|---|---|---|---|
| Failure-related | `CHANGE_CODE` 211, 215, 216, 217, or 230; `FAILURE=1`; or `FAILURE_ROLE=1` | Official failure-related structural event | Later label policy must determine timing and prevent leakage |
| Voluntary closure | Code 240 or `VOLUNTARY_LIQ=1` | Voluntary liquidation/closure | Distinct from failure |
| Merger | Codes 221–224, 810, 811; merger flags; or `UNASSISTED_COMBO=1` | Institution merger or unassisted combination | Branch acquisitions are not automatically mergers |
| Acquisition | Codes 712, 713, 722; acquisition flags; or populated `ACQ_CERT` | Acquisition, sale, or branch transaction | 10,751 acquisition rows have no canonical institution CERT; their branch/transaction evidence is retained |
| Name change | Code 510 or `NAME_CHANGE=1` | Legal or reported name change | Does not create a new institution key |
| Charter change | Codes 420 or 430; class/charter flags | Charter agency or class change | Not a failure or merger |
| Regulator change | Code 470 or regulator-change flags | Primary regulator change | OTS-era transitions require historical context |
| Other | A described event without a mapped category | Traceable residual category | Review before any downstream use |
| Unclassified | No usable code, description, or mapped flag | Insufficient evidence | Never silently recoded |

Priority is failure-related, voluntary closure, merger, acquisition, name, charter, regulator, then residual. This prevents an event carrying several flags from being treated as a benign name change when official failure evidence is present.

Observed Phase 2 rows: Other 192,911; Failure-related 95,046; Acquisition 24,983; Merger 16,562; Name change 11,226; Charter change 10,032; Voluntary closure 702; Regulator change 645. These counts describe history records, not unique banks or exits.
