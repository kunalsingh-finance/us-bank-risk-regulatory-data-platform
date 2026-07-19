# Phase 2 Data-Quality Control Inventory

Controls are implemented in `sql/013_run_data_quality_controls.sql`. Exceptions are preserved in `quality.data_quality_exceptions`; no source row is removed. A blocking control prevents approval when its evidence represents an unresolved structural contradiction.

| ID | Control / objective | Input and condition | Severity | Expected | Treatment | Blocking |
|---|---|---|---|---|---|---|
| DQ001 | Unique bank-quarter key | Fact; duplicate CERT + reporting date | Critical | 0 | Investigate source/pagination | Yes |
| DQ002 | CERT completeness | Fact CERT is null | Critical | 0 | Stop build | Yes |
| DQ003 | RSSDID completeness | Fact RSSDID is null | High | 0 | Stop build | Yes |
| DQ004 | Date completeness | Fact reporting date is null | Critical | 0 | Stop build | Yes |
| DQ005 | Quarter-end date | Date differs from month end or month not 3/6/9/12 | High | 0 | Stop build | Yes |
| DQ006 | Approved coverage | Date outside 2001-03-31–2026-03-31 | Critical | 0 | Stop build | Yes |
| DQ007 | Current-reference coverage | Financial CERT absent from current institutions | Informational | Explain | Retain historical bank | No |
| DQ008 | Failure-history coverage | Failure/assistance CERT absent from financials | Informational | Explain | Retain left-censored record | No |
| DQ009 | History identifier resolution | No parseable CERT role | Informational | Explain | Retain branch/transaction event | No |
| DQ010 | Concurrent RSSDID conflict | One RSSDID maps to different CERTs in overlapping periods | High | 0 | Investigate collision | Yes |
| DQ011 | CERT/RSSDID change | CERT maps to multiple RSSDIDs | Medium | Review | Preserve sequence | No |
| DQ012 | Reported name changes | CERT has several quarter-reported names | Informational | Review | Use event history, never name key | No |
| DQ013 | Sequential RSSDID succession | RSSDID maps to different CERTs without overlap | Informational | Review | CERT stays primary; preserve succession | No |
| DQ020 | Nonnegative assets | Assets below zero | Critical | 0 | Stop and investigate | Yes |
| DQ021 | Nonnegative deposits | Deposits below zero | High | 0 | Preserve and investigate | No |
| DQ022 | Nonnegative gross loans | Gross loans below zero | High | 0 | Preserve and investigate | No |
| DQ023 | Negative equity review | Equity below zero | Medium | Possible distress | Preserve; denominator protection later | No |
| DQ024 | Loans/assets plausibility | Gross loans exceed assets | Medium | Rare | Preserve; investigate definitions | No |
| DQ025 | Deposit/assets plausibility | Deposits exceed 1.5 × assets | Low | Rare | Preserve; configurable threshold | No |
| DQ026 | Broad percentage bound | Selected quarterly percentage absolute value >100 | Low | Rare | Preserve; inspect denominator/unit | No |
| DQ027 | All-null financial row | All principal balances null | High | 0 | Stop and inspect extraction | Yes |
| DQ030 | Quarter gap | Consecutive observations differ by more than one quarter | Informational | Explain | Preserve entry/exit/re-entry | No |
| DQ031 | Later-quarter post-failure record | `RESTYPE=FAILURE` and observation quarter follows closing quarter | High | 0 | Investigate CERT reuse/timing | Yes |
| DQ032 | Failure before first panel row | No financial row or closing precedes first row | Informational | Explain | Document left censoring | No |
| DQ033 | Row after current inactive date | Financial date follows current-file inactive date | Low | Review | Preserve; current attributes are not historical | No |
| DQ034 | Same-quarter failure timing | Quarter-end date follows exact closing date within same quarter | Informational | Review | Preserve for later timing policy | No |

Phase 2 observed no Critical or High exceptions after distinguishing the 13 official `ASSISTANCE` records from 579 `FAILURE` records and distinguishing sequential RSSDID succession from concurrent conflict. Known limitations: plausibility thresholds are broad screens, current institution attributes are not point-in-time dimensions, and branch-heavy history events may lack an institution CERT.
