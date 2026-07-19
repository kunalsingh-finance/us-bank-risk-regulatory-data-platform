# Architecture

## End-to-end lineage

```mermaid
flowchart TD
    A["FDIC BankFind Suite and API"] --> B["Raw pages and source hashes"]
    B --> C["Quarter validation and normalized Parquet"]
    C --> D["DuckDB staging"]
    D --> E["Core institution and bank-quarter tables"]
    E --> F["Quality exceptions and reconciliations"]
    E --> G["Risk-feature SQL"]
    G --> H["Same-quarter peer benchmarks"]
    E --> I["Failure, censoring, competing-exit SQL"]
    H --> J["Chronological model datasets"]
    I --> J
    J --> K["Training and expanding validation"]
    K --> L["Frozen selection"]
    L --> M["One-time locked test"]
    M --> N["Ranking presentation tables"]
    N --> O["Streamlit research dashboard"]
```

## Locked-test isolation

```mermaid
sequenceDiagram
    participant T as Training window
    participant V as Validation folds
    participant S as Frozen selection
    participant L as Locked 2019Q1-2024Q4 test
    T->>V: Fit preprocessing and candidates chronologically
    V->>S: Select model and monitoring budget
    S->>L: Hash protocol, then access once
    L-->>S: Frozen metrics, predictions, uncertainty, subgroups
    Note over S,L: No post-test tuning or recalibration
```

## Public dashboard flow

```mermaid
flowchart LR
    A["Deterministic synthetic bank rows"] --> C["Public demo Parquet"]
    B["Frozen aggregate validation evidence"] --> C
    C --> D["DuckDB pushdown queries"]
    D --> E["Eight Streamlit pages"]
    E --> F["Persistent demo and ranking-only notices"]
```

Schemas separate raw, staging, core, quality, audit, and reporting concerns. Python orchestrates transactions, manifests, tests, and exports; the principal data model, ratios, temporal logic, peers, censoring, and labels remain in SQL.
