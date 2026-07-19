# Dashboard User Guide

Start the app with:

```powershell
python scripts/run_dashboard.py
```

The app reads prepared files under `data/processed/dashboard/`. Run `python scripts/build_dashboard_data.py` and `python scripts/validate_dashboard_data.py` before startup when those files are absent.

Use Executive Overview to choose a historical scored quarter and review tier, size-band, class, and quality distributions. Current Watchlist shows the latest frozen top-5% monitoring population. Bank Detail provides an eight-quarter percentile and feature history. Peer Comparison uses only the selected bank's reporting quarter. Model Validation displays the exact locked-test evidence. Failure Case Studies deliberately include captured, missed, and false-positive examples. Data Quality exposes hashes and warnings; Methodology explains interpretation boundaries.

Read percentiles as relative public-data indicators, not an institution-level event likelihood. The app supports analyst prioritization and historical demonstration only.
