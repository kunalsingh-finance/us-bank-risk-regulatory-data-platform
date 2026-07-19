# Security and Privacy Scan

The release process scans candidate text for credential forms, private keys, tokens, secret assignments, user-home paths, download/temporary paths, private runtime metadata, and prohibited binaries. It inventories Git history without rewriting it.

Institution-level public demo records are generated inside a reserved synthetic identifier range and use names of the form `Synthetic Bank NNN` with state `DEMO`. Real active-bank rankings, historical bank-level prediction rows, raw source responses, model binaries, databases, logs, caches, browser output, secrets files, and local environment files are excluded.

Reports are written to `reports/public_release_*_scan.csv`; the clean-candidate result is recorded in `public_release/PUBLIC_RELEASE_QUALITY_GATE.json`. A scan pass is not a guarantee against all security defects. Any discovered credential must be removed from files, rotated at its provider, and reviewed in Git history before publication.
