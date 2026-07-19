# Phase 2 Source-to-Target Mapping

Null handling is uniform unless noted: trim source text; convert empty text to null; use `TRY_CAST` only with a companion parse-status/control path; never replace null with zero. SQL file names are the transformation versions.

## Financial panel to `core.bank_quarter_financials`

Source table: `staging.financials`. SQL: `sql/009_build_bank_quarter_fact.sql`. Validation: 698,804 input rows equal 698,804 target rows; CERT + reporting date is unique; parse failures are zero.

| Source field(s) | Target field(s) | Type / transformation | Validation and caveat |
|---|---|---|---|
| CERT, RSSDID | cert, rssdid | BIGINT parsed in staging | Both required; CERT is primary, RSSDID secondary |
| NAMEFULL | institution_name | trimmed VARCHAR | Display/audit only; never a join key |
| REPDTE | reporting_date | YYYYMMDD to DATE | Required approved quarter-end |
| STALP, BKCLASS, REGAGNT | state, bank_class, primary_regulator | trimmed VARCHAR | Time-varying reported attributes |
| ACTIVE | active_status | `1` true, `0` false, else null | Status is not a failure label |
| ASSET, EQ, EQTOT | asset, equity, total_equity | DECIMAL(38,6), direct parse | USD thousands; no ratio calculated |
| LNLSGR, LNLSNET | gross_loans_leases, net_loans_leases | DECIMAL(38,6), direct parse | USD thousands |
| P3ASSET, P9ASSET, NAASSET, ORE | past_due_30_89, past_due_90_plus, nonaccrual_assets, other_real_estate | DECIMAL(38,6), direct parse | Zero preserved; null not imputed |
| CHBAL, SC | cash_balances, securities | DECIMAL(38,6), direct parse | USD thousands |
| DEP, DEPDOM, DEPCSBQ | deposits, domestic_deposits, assessable_deposits | DECIMAL(38,6), direct parse | USD thousands |
| FREPO, OTHBFHLB | fed_funds_reverse_repos, fhlb_advances | DECIMAL(38,6), direct parse | USD thousands |
| LNRECONS, LNREMULT, LNRERES | construction_loans, multifamily_loans, residential_loans | DECIMAL(38,6), direct parse | USD thousands |
| LNCI, LNCON, LNCRCD | commercial_industrial_loans, consumer_loans, credit_card_loans | DECIMAL(38,6), direct parse | USD thousands |
| NIMQ, NIMYQ | quarterly_net_interest_income, quarterly_net_interest_margin | DECIMAL(38,6), direct parse | Official quarterly fields; not YTD substitutes |
| NETINCQ, NONIIQ, NONIXQ, PTAXNETINCQ | quarterly_net_income, quarterly_noninterest_income, quarterly_noninterest_expense, quarterly_pretax_income | DECIMAL(38,6), direct parse | Quarterly source flows |
| ROAQ, EEFFQR, INTEXPYQ, NTLNLSQ | quarterly_return_on_assets, quarterly_efficiency_ratio, quarterly_funding_cost, quarterly_net_chargeoffs | DECIMAL(38,6), direct parse | Official quarterly measures; values preserved |
| requested_quarter, ingestion_run_id, configuration_hash, quarter_raw_hash | source_quarter, source_run_id, source_configuration_hash, source_raw_hash | direct lineage copy | Required lineage |
| source_manifest_path, extraction_timestamp, downloader_version, normalization_version, validation_status | same names | direct lineage copy | Required lineage |
| build constants | source_file, source_sha256, build_run_id, build_configuration_hash, sql_version | frozen build metadata | Non-null controls |

## Institution CSV to `core.institutions`

Source table: `staging.institutions`. SQL: `sql/008_build_institution_dimension.sql`.

| Source | Target | Transformation | Rule / caveat |
|---|---|---|---|
| CERT, FED_RSSD | cert, rssdid | BIGINT parse | CERT unique; RSSDID may be null in current file |
| NAME, CITY, STALP, BKCLASS, REGAGNT | institution_name, city, state, bank_class, primary_regulator | trim | Current-state reference, not historical truth |
| ESTYMD, ENDEFYMD | established_date, inactive_date | MM/DD/YYYY to DATE | Invalid text is reported |
| ACTIVE | active_status | `1`/`0` to BOOLEAN | Current status only |
| ASSET | current_asset_size | DECIMAL(38,6) | Never forward-filled into bank quarters |
| source fields/constants | source_record_date, source_file, ingestion_run_id, source_record_reference, source_sha256, build_configuration_hash, sql_version | direct / frozen metadata | Complete lineage |

## History CSV to `core.institution_history_events`

Source table: `staging.history_events`. SQL: `sql/010_build_history_events.sql`.

| Source | Target | Transformation | Rule / caveat |
|---|---|---|---|
| ID, TRANSNUM | history_event_id, transaction_number | BIGINT parse | Source event identifiers retained |
| CERT, FRM_CERT, OUT_CERT, SUR_CERT, ACQ_CERT | cert and role-specific identifiers | BIGINT parse; canonical CERT uses documented precedence | Missing canonical CERT is retained as DQ009 |
| EFFDATE, CHANGE_CODE, CHANGE_DESC | event_date, event_code, event_description | date parse / trim | Code and description always retained |
| role names and flags | predecessor/successor names, raw flags | trim / direct | Official evidence remains auditable |
| codes + official flags | event_taxonomy | CASE in SQL 010 | Descriptive taxonomy only; no outcome label |
| source fields/constants | lineage fields | direct / frozen metadata | Complete lineage |

## Failure file to `core.bank_failures_reference` and `core.bank_exits_reference`

Source table: `staging.failures`. SQL: `sql/011_build_failure_reference.sql`.

| Source | Target | Transformation | Rule / caveat |
|---|---|---|---|
| ID, CERT | failure_record_id, cert | BIGINT parse | Both source identifiers retained |
| NAME, CITY, PSTALP | institution_name, city, state | trim | Descriptive only |
| FAILDATE | closing_date | MM/DD/YYYY to DATE | Exact date retained |
| BIDNAME, FUND, FIN | acquiring_institution, fund_number, financial_institution_number | trim / BIGINT parse | Null preserved |
| RESTYPE, RESTYPE1 | resolution_type, resolution_type_code | trim | 579 FAILURE and 13 ASSISTANCE; assistance is not failure |
| failure/history evidence | exit_classification | explicit CASE/taxonomy mapping | Merger and assistance remain distinct from FDIC failure |
| source fields/constants | lineage fields | direct / frozen metadata | Complete lineage |

No Phase 2 target contains imputed financial values, ratios, lags, predictive labels, peer percentiles, or model outputs.
