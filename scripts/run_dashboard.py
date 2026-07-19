"""Start the prepared-data Streamlit dashboard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]


def main() -> None:
    command: list[str] = [sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboards/app.py"), "--server.headless=true", "--browser.gatherUsageStats=false"]
    raise SystemExit(subprocess.call(command, cwd=ROOT))


if __name__ == "__main__":
    main()
