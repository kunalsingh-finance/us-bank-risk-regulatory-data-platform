"""Build and report the Phase 2 DuckDB database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.builder import BuildResult, build_database  # noqa: E402
from src.database.manifest import JsonObject, load_json_object, write_replaceable_json  # noqa: E402
from src.database.reporting import export_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    arguments = parser.parse_args()
    result: BuildResult = build_database(ROOT, arguments.config.resolve())
    report_hashes: dict[str, str] = export_reports(result.database_path, ROOT / "reports")
    manifest_path: Path = ROOT / "manifests" / "database_build" / "run_manifest.json"
    manifest: JsonObject = load_json_object(manifest_path)
    manifest["report_hashes"] = report_hashes
    write_replaceable_json(manifest_path, manifest)
    print(f"PASS database={result.database_path} sha256={result.database_sha256}")
    print(f"PASS configuration_hash={result.configuration_hash} reports={len(report_hashes)}")


if __name__ == "__main__":
    main()
