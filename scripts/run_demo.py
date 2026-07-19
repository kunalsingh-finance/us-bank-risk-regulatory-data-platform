"""Start the dashboard with deterministic publication-safe data."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]


def demo_environment() -> dict[str, str]:
    environment: dict[str, str] = dict(os.environ)
    environment["BANK_RISK_DEMO_MODE"] = "1"
    environment["BANK_RISK_DASHBOARD_DATA_DIR"] = str(ROOT / "public_release/data")
    return environment


def main() -> None:
    port: str = os.environ.get("BANK_RISK_DEMO_PORT", "8501")
    command: list[str] = [
        sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboards/app.py"),
        "--server.headless=true", "--browser.gatherUsageStats=false", f"--server.port={port}",
    ]
    raise SystemExit(subprocess.call(command, cwd=ROOT, env=demo_environment()))


if __name__ == "__main__":
    main()

