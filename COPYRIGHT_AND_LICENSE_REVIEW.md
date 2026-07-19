# Copyright and License Review

Review date: 2026-07-19. This is a conservative engineering review, not legal advice.

## Decision

Project-authored code and documentation may be released under MIT. No third-party code was vendored and no incompatible snippet was identified. Data and generated artifacts are separately governed.

The FDIC presents BankFind Suite, bulk downloads, and a public API as public-data tools, but the reviewed pages did not provide an explicit redistribution license covering copied CSV, raw API-response archives, definition workbooks, or spreadsheets. The FDIC also states that it does not certify the accuracy of the data and that the data do not indicate regulatory approval, disapproval, or rating. Consequently, copied source artifacts are excluded and the release includes official links, downloader code, schemas/configurations, deterministic synthetic records, and aggregate analytical evidence.

Official references reviewed:

- FDIC Bank Data Guide: https://www.fdic.gov/resources/tools/bank-data-guide
- FDIC BankFind Suite: https://banks.data.fdic.gov/bankfind-suite/
- FDIC bulk data: https://banks.data.fdic.gov/bankfind-suite/bulkData
- FDIC disclaimers and methodologies: https://banks.data.fdic.gov/bankfind-suite/help?helpTopic=disclaimers-and-methodologies
- FDIC Open Government: https://www.fdic.gov/open-government

## Artifact decisions

| Artifact | Decision | Rationale |
|---|---|---|
| FDIC bulk CSV and API-response pages | Exclude | Raw redistribution permission not established; large and unnecessary for review. |
| FDIC YAML/CSV definitions and financial-report workbook | Exclude copied files | Provide official source links and project-authored mappings. |
| Full financial and peer panels | Exclude | Large generated institution-level datasets; reproducible locally. |
| DuckDB and serialized model files | Exclude | Generated binaries are unnecessary and serialized models carry supply-chain risk. |
| Synthetic demo Parquet | Include | Project-authored deterministic records, clearly marked synthetic. |
| Frozen validation aggregates | Include | Project-generated aggregate research evidence; no institution-level prediction disclosure. |
| Academic papers | Cite only | No paper files are bundled. |
| Images, logos, fonts, screenshots | Exclude unless project-authored and reviewed | None are required by the candidate. |

The MIT License does not transfer ownership of source data, package code, trademarks, or third-party materials.
