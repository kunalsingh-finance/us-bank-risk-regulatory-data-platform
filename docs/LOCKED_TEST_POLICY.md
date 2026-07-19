# Locked-Test Policy

The locked test is 2019 Q1–2024 Q4. Its targets are stored as null and its statuses as `LOCKED_TEST_MASKED` in modelling datasets. Test outcomes may be joined from the immutable Phase 4 database only by `scripts/run_locked_test.py` after the pre-test selection manifest is complete, committed, and tagged `phase5-pre-test-model-frozen`.

The script writes `STARTED` before reading outcomes and permits no more than one `COMPLETED` access. The same access evaluates the frozen four-quarter model, eight-quarter secondary model, and deterioration sensitivity model. After completion, features, model family, hyperparameters, calibration, threshold, budgets, and split dates cannot change. A genuine implementation defect requires explicit invalidation and a complete new freeze; disappointing performance does not.
