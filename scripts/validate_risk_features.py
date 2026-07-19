"""Validate a completed Phase 3 feature database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features.builder import feature_names  # noqa: E402
from src.features.manifest import load_hashed_configuration, require_int, require_string  # noqa: E402
from src.features.validator import validate_feature_database  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--risk-config", required=True, type=Path)
    arguments = parser.parse_args()
    config = load_hashed_configuration(arguments.risk_config.resolve())
    database_path: Path = ROOT / require_string(config, "output_database")
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        results = validate_feature_database(connection, require_int(config, "expected_rows"), len(feature_names(config)))
    finally:
        connection.close()
    print(f"PASS validations={len(results)} database={database_path}")


if __name__ == "__main__":
    main()
