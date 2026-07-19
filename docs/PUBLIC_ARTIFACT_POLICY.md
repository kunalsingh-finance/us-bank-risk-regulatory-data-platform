# Public Artifact Policy

| Class | Public treatment |
|---|---|
| Source code, SQL, configurations, tests | Include after secret, path, and claim scans. |
| Research and governance documentation | Include when factual, relative-path safe, and free of private metadata. |
| Aggregate reports | Include only after field-level review confirms no institution-level ranking or sensitive identifier disclosure. |
| Demo data | Include only deterministic synthetic institution rows and frozen aggregate validation evidence. |
| Raw/bulk/API source copies | Exclude; provide official download links and reproducible code. |
| Full generated panels and peer tables | Exclude; rebuild locally. |
| DuckDB, serialized models, predictions | Exclude; provide methods, hashes, and aggregate evidence. |
| Logs, caches, environments, secrets, browser artifacts | Exclude. |

The public candidate is built from an explicit allowlist. Existing Git tracking is not evidence of publication approval. `PUBLICATION_INVENTORY.csv` records the file-level review and `public_release/RELEASE_FILE_INVENTORY.csv` records the actual candidate.
