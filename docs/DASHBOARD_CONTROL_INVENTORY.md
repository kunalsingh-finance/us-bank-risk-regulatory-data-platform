# Dashboard Control Inventory

| Control | Objective | Blocking condition |
|---|---|---|
| DSH001 | Verify immutable Phase 3–5 and model-artifact hashes | Any mismatch |
| DSH002 | Enforce one score per CERT and quarter | Duplicate key |
| DSH003 | Keep percentiles within 0–100 | Out-of-range value |
| DSH004 | Restrict rank population to the same quarter | Cross-quarter population |
| DSH005 | Reconcile top 1%, 5%, and 10% locked counts | Count mismatch |
| DSH006 | Reproduce frozen raw scores | Nonzero maximum difference |
| DSH007 | Link every driver to its bank-quarter and approved feature | Missing or prohibited feature |
| DSH008 | Enforce peer-quarter alignment and warnings | Date mismatch or suppressed warning |
| DSH009 | Preserve captured and missed case studies | Missing case family |
| DSH010 | Reconcile displayed frozen metrics | Numeric difference |
| DSH011 | Validate required Parquet schemas and lineage fields | Missing file or column |
| DSH012 | Scan misleading language | Any unresolved finding |
| DSH013 | Start and load every Streamlit page | Traceback or page failure |
| DSH014 | Confirm logical rebuild reproducibility | Row-count or hash difference |

Exceptions remain in `reports/dashboard_quality_exceptions.csv`; they are not silently removed.
