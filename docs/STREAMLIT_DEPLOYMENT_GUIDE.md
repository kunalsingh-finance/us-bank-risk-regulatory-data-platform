# Streamlit Deployment Guide

## Local Windows startup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\build_dashboard_data.py
.\.venv\Scripts\python.exe scripts\validate_dashboard_data.py
.\.venv\Scripts\python.exe scripts\run_dashboard.py
```

The prepared Parquet directory, not raw files or generated DuckDB binaries, is the dashboard runtime dependency. Public deployment is not authorized in Phase 6. Phase 7 must decide which aggregate or sampled tables may be distributed, remove local metadata, and review data licensing.

For a local desktop, keep the repository and `.venv` on a fast disk. The app filters Parquet with DuckDB before materialization and caches read-only results. Missing files and schema mismatches raise actionable startup errors.
