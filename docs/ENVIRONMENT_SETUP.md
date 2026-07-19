# Environment Setup

Supported baseline: CPython 3.11 or newer. The release candidate pins the validated package versions in `requirements.txt`; developer tools are in `requirements-dev.txt`.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\validate_environment.py
```

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_environment.py
```

No editable local package, credential, or environment-specific path is required. The demo reads checked-in synthetic Parquet tables. A full rebuild requires internet access to the official FDIC service and substantially more storage and time.
