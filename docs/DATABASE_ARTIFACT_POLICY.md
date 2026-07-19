# Database Artifact Policy

`database/bank_risk.duckdb` is generated, git-ignored, and retained locally. It must not be committed automatically because it is large, reproducibly derived, and contains copied regulatory data. The repository tracks the build configuration, SQL, Python orchestration, tests, manifest, reports, and documentation needed to recreate and verify it.

Build with:

```powershell
.\.venv\Scripts\python.exe scripts\build_database.py --config configs\database_build.yaml
```

The builder writes an owned temporary database, executes all SQL in one transaction, validates row/key controls, commits only on success, closes the file, and atomically replaces the prior local artifact. It never edits an input file. A failed build rolls back and deletes only its owned temporary file. Rebuild validation uses database structural results and deterministic exported report hashes; the binary SHA-256 is also recorded for the specific build.
