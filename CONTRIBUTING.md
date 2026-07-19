# Contributing

Contributions are welcome when they preserve the project's data, model, and claim-governance boundaries.

1. Open an issue describing the defect or proposed change.
2. Use a focused branch and keep source data, generated databases, model binaries, and real institution-level prediction outputs out of commits.
3. Add or update the smallest meaningful test. Public checks must run against `public_release/data/`.
4. Run `python -m pytest -q tests/public_release` and the public quality gate.
5. Document changes to financial definitions, labels, evaluation periods, or claims explicitly.

Do not alter frozen metrics, reopen the governed locked test, relabel mergers as failures, call indicators official CAMELS ratings, or present rankings as calibrated failure probabilities. Security concerns should not include live secrets or sensitive bank-level exports in an issue.
