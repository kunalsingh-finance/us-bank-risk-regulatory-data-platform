# Label Quality Control Inventory

| ID | Control | Expected | Blocking | Treatment |
|---|---|---:|---|---|
| LC001 | Failure labels reconcile to canonical rows | 698,804 | Yes | Roll back build |
| LC002 | Distress labels reconcile to canonical rows | 698,804 | Yes | Roll back build |
| LC003 | Duplicate CERT/reporting-date keys | 0 | Yes | Roll back build |
| LC004 | Four-quarter right-censored non-null binaries | 0 | Yes | Roll back build |
| LC005 | Eight-quarter right-censored non-null binaries | 0 | Yes | Roll back build |
| LC006 | Assistance records overlapping validated failures | 0 | Yes | Roll back build |
| LC007 | Negative days until failure | 0 | Yes | Roll back build |
| LC008 | Positive labels at/before predictor date | 0 | Yes | Roll back build |
| LC009 | Failed leakage controls | 0 | Yes | Roll back build |
| LL001 | Prohibited outcome columns in predictor table | 0 | Yes | Stop modelling |
| LL002 | Feature observations at/after validated failure | 0 | Yes | Stop modelling |
| LL003 | Future outcome evidence outside separate tables | 0 | Yes | Stop modelling |
| LL004 | Future peer statistics used | 0 | Yes | Stop modelling |

Expected censoring and unmatched out-of-coverage failures are preserved in dedicated exception tables rather than treated as data defects.
