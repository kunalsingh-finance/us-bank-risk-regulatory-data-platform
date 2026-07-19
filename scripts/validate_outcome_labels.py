"""Validate an already-built Phase 4 label database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.labels.manifest import load_hashed_configuration, require_int  # noqa: E402
from src.labels.validator import validate_label_database  # noqa: E402


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--label-config", required=True, type=Path)
    arguments: argparse.Namespace = parser.parse_args()
    config = load_hashed_configuration(arguments.label_config.resolve())
    database_path: Path = ROOT / str(config["output_database"])
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path), read_only=True)
    results = validate_label_database(connection, require_int(config, "expected_rows"))
    connection.close()
    print(f"PASS validations={len(results)} database={database_path}")


if __name__ == "__main__":
    main()
