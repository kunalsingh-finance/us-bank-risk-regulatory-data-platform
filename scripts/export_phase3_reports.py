"""Export deterministic Phase 3 reports from the completed feature database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features.manifest import load_hashed_configuration, require_string  # noqa: E402
from src.features.reporting import export_feature_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--risk-config", required=True, type=Path)
    arguments = parser.parse_args()
    config = load_hashed_configuration(arguments.risk_config.resolve())
    hashes: dict[str, str] = export_feature_reports(
        ROOT, ROOT / require_string(config, "output_database"), arguments.risk_config.resolve()
    )
    for filename, digest in sorted(hashes.items()):
        print(f"{digest}  {filename}")


if __name__ == "__main__":
    main()
