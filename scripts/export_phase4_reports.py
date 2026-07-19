"""Re-export deterministic Phase 4 reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.labels.manifest import load_hashed_configuration  # noqa: E402
from src.labels.reporting import export_label_reports  # noqa: E402


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--label-config", required=True, type=Path)
    arguments: argparse.Namespace = parser.parse_args()
    config = load_hashed_configuration(arguments.label_config.resolve())
    hashes: dict[str, str] = export_label_reports(ROOT, ROOT / str(config["output_database"]))
    print(f"PASS reports={len(hashes)}")


if __name__ == "__main__":
    main()
