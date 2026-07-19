"""Validate a completed Phase 2 DuckDB database and immutable inputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.builder import SourceFile, parse_sources, require_string, validate_source_hashes  # noqa: E402
from src.database.manifest import JsonObject, load_json_object, sha256_file  # noqa: E402
from src.database.validator import ValidationResult, validate_database  # noqa: E402


def expected_rows(sources: tuple[SourceFile, ...], name: str) -> int:
    matches: list[SourceFile] = [source for source in sources if source.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected one source named {name}; found {len(matches)}")
    return matches[0].expected_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    arguments = parser.parse_args()
    config: JsonObject = load_json_object(arguments.config.resolve())
    sources: tuple[SourceFile, ...] = parse_sources(ROOT, config)
    validate_source_hashes(sources)
    database_path: Path = ROOT / require_string(config, "database_path")
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        results: tuple[ValidationResult, ...] = validate_database(
            connection,
            expected_rows(sources, "financials"),
            expected_rows(sources, "institutions"),
            expected_rows(sources, "history_events"),
            expected_rows(sources, "failures"),
        )
    finally:
        connection.close()
    print(f"PASS validations={len(results)} database_sha256={sha256_file(database_path)}")


if __name__ == "__main__":
    main()
