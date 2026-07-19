# Reproducibility Guide

The project separates two reproducibility modes.

## Immediate demonstration

`scripts/run_demo.py` reads checked-in, hash-manifested synthetic tables. Rebuilding those tables from the governed development workspace is deterministic. This mode demonstrates interface behavior, data lineage, peers, drivers, quality flags, and exact aggregate validation summaries without exposing active-bank rankings.

## Full logical reconstruction

`configs/full_pipeline.yaml` declares the ordered official-source, SQL, feature, label, experiment, and dashboard stages. External downloads are source-version dependent, so later retrieval can be logically equivalent without matching 2026 bytes. Frozen evidence is identified by hashes and is not recomputed during Phase 7.

## Reproducibility definitions

- Exact artifact reproducibility: identical input bytes, code, configuration, package versions, ordering, and hashes.
- Logical reproducibility: the same documented transformations and controls applied to officially retrieved source versions.
- Demonstration reproducibility: identical synthetic tables and dashboard behavior from the checked-in public package.

Every governed layer uses configuration hashes, deterministic ordering, row-count reconciliation, uniqueness controls, and build manifests. Environment validation, public tests, and the clean-candidate quality gate are the entry points for reviewers.
