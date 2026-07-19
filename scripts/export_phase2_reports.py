"""Re-export deterministic Phase 2 reconciliation reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.builder import require_string  # noqa: E402
from src.database.manifest import JsonObject, load_json_object  # noqa: E402
from src.database.reporting import export_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    arguments = parser.parse_args()
    config: JsonObject = load_json_object(arguments.config.resolve())
    hashes: dict[str, str] = export_reports(ROOT / require_string(config, "database_path"), ROOT / "reports")
    for filename, digest in sorted(hashes.items()):
        print(f"{digest}  {filename}")


if __name__ == "__main__":
    main()
