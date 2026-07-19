"""Build all prepared Phase 6 dashboard presentation tables."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.builder import build_dashboard_data  # noqa: E402


def main() -> None:
    manifest = build_dashboard_data(ROOT)
    tables: object = manifest["presentation_tables"]
    print(f"PASS run_id={manifest['dashboard_build_run_id']} tables={len(tables) if isinstance(tables, dict) else 0}")


if __name__ == "__main__":
    main()
