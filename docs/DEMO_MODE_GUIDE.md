# Demonstration Mode Guide

Run:

```powershell
python scripts\validate_environment.py
python scripts\run_demo.py
```

Demonstration mode sets `BANK_RISK_DEMO_MODE=1` and points `BANK_RISK_DASHBOARD_DATA_DIR` to `public_release/data`. It needs no raw download, database, model binary, training run, or active-bank prediction file.

Every page displays a demonstration banner. Institution names, identifiers, states, rankings, histories, peers, drivers, quality flags, and case studies are deterministic synthetic examples. The Model Validation page uses frozen aggregate historical research results; those statistics do not describe the synthetic cases. The app remains ranking-only and never displays a calibrated failure probability.

To choose another local port, set `BANK_RISK_DEMO_PORT` before starting. Stop the process with Ctrl+C.
