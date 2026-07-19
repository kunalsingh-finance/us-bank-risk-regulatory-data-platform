# Feature Quality Control Inventory

| Control | Objective | Evidence / expected result | Blocking |
|---|---|---|---|
| FQ001 | Feature row reconciliation | 698,804 feature rows | Yes |
| FQ002 | Canonical key uniqueness | 698,804 distinct CERT-date keys | Yes |
| FQ003 | Quality-row reconciliation | 698,804 quality rows | Yes |
| FQ004 | Peer-group reconciliation | 698,804 peer-group rows | Yes |
| FQ005 | Identifier completeness | Zero missing feature CERTs | Yes |
| FQ006 | Temporal direction | Zero prior/year-ago dates on or after current date | Yes |
| FQ007 | Percentile bounds | Every available percentile in [0,1] | Yes |
| FQ008 | Same-quarter peers | Peer-group ID begins with current reporting date | Yes |
| FQ009 | Outcome isolation | No failure-named column in feature table | Yes |
| FQ010 | Finite values | Zero infinities in selected derived features | Yes |

Detailed flags remain separate columns and exception rows: missing numerator, missing/zero/negative denominator, insufficient lag, insufficient rolling history, conditional field unavailable, small peer group, preserved extreme, suspected unit issue, identifier continuity, and source-field warning.

Observed feature exceptions were 77,022 Informational, 1,805 Low, and 5,877 Medium, with no Critical or High exception class. The large Informational population is expected because first observations cannot have lags and small detailed peer groups trigger documented fallback. No exception removes a bank-quarter.
