# Project Specification

## Title

U.S. Bank Risk Early-Warning & Regulatory Data Platform

## Research question

Can public regulatory financial data identify early signs of deterioration in U.S. banks before FDIC failure or severe financial distress?

## Purpose and boundaries

This public-data banking-risk and financial-data research platform combines banking interpretation, SQL data modelling, controls, reproducibility, transparent rare-event modelling, and management reporting. It is a research implementation, not a regulatory assessment or production supervisory system.

The analytical framework must always be called a **public-data CAMELS-style risk indicator framework**. Actual CAMELS ratings are confidential and are not available here.

## In scope

- FDIC BankFind Suite institution, financial, failure, and history data.
- One controlled row per `CERT` and reporting quarter.
- DuckDB tables and transparent SQL transformations.
- Failure-versus-merger/exit classification.
- Capital, asset quality, earnings, liquidity/funding, concentration, trend, and peer features.
- Official public macroeconomic data after the bank panel passes quality gates.
- Chronological rare-event modelling, calibration, threshold analysis, and explainable alerts.
- Streamlit monitoring dashboard and reproducible reports.
- Public-release safety and evidence-based documentation after validation.

## Out of scope and prohibited claims

- Official CAMELS ratings, regulatory approval, production supervision, investment advice, guaranteed failure prediction, or causal claims from model importance.
- Random splits, shuffled validation, future leakage, full-sample preprocessing, merger-as-failure labels, or test-set tuning.
- Accuracy as the primary rare-event metric.
- Publishing credentials, local paths, restricted raw data, or unsupported analytical claims.

## Analytical keys and grain

- Institution master: one row per source institution record, keyed primarily by `CERT` with secondary identifiers retained.
- Quarterly panel: one row per `CERT × reporting_quarter`.
- Failure event: one row per FDIC failure record, joined by `CERT` and parsed failure date.
- Structure event: one row per source `ID`, retaining `TRANSNUM`, `UNINUM`, surviving/outgoing/acquiring certificates, and event codes.

## Planned architecture

1. Immutable FDIC raw files and API response cache.
2. Validated staging with explicit types, sentinel handling, and lineage.
3. DuckDB core tables and bank-quarter panel built in SQL.
4. Data-quality exceptions retained rather than silently dropped.
5. Leakage-safe labels, features, peer benchmarks, and macro joins.
6. Frozen chronological experiment protocol before locked-test access.
7. Transparent models, validation, alerts, dashboard, and release package.

## Phase gates

| Phase | Branch | Exit condition |
|---|---|---|
| 0 Source audit | `phase0-source-audit` | Files located, copied, hashed, profiled, mapped, and field/downloader plans documented |
| 1 Data ingestion | `phase1-data-ingestion` | Resumable API client passes pagination, retry, schema, row-count, and checksum controls |
| 2 SQL data model | `phase2-sql-data-model` | DuckDB tables and unique bank-quarter panel reconcile to raw sources |
| 3 Risk features | `phase3-risk-features` | SQL ratios, trends, and peer benchmarks pass hand checks |
| 4 Labels and validation | `phase4-labels-and-validation` | Failures link reliably; mergers/exits excluded; label audit passes |
| 5 Model development | `phase5-model-development` | Protocol is hashed; validation-only selection completed; locked test untouched until final evaluation |
| 6 Economic diagnostics | `phase6-economic-diagnostics` | Time/size/stress diagnostics and macro sensitivity documented |
| 7 Dashboard | `phase7-dashboard` | All pages load from validated tables and show lineage/quality status |
| 8 Public release | `phase8-public-release` | License, privacy, secret, clean-clone, and quality gates pass |

## Model-risk principles

- Labels use only future outcomes relative to the observation quarter; predictors use information available at or before that quarter.
- Missing-value fitting, scaling, sampling, and threshold selection occur inside each training/validation window.
- Models are evaluated with PR AUC, ROC AUC, Brier score, calibration, recall/precision at top-risk shares, lead time, alert stability, and cost-weighted errors.
- All preregistered models and negative results are reported.
- Alerts say “elevated public-data risk indicators,” never “will fail.”

## Phase 0 acceptance status

The required folder structure, immutable source copies, source manifest, audit, preliminary dictionary, 50-field shortlist, and downloader plan exist. Full ingestion and modelling remain intentionally unstarted.

