"""Build the Phase 3 feature database and deterministic reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, load_json_object, write_replaceable_json  # noqa: E402
from src.features.builder import FeatureBuildResult, build_feature_database  # noqa: E402
from src.features.reporting import export_feature_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--risk-config", required=True, type=Path)
    parser.add_argument("--peer-config", required=True, type=Path)
    parser.add_argument("--quality-config", required=True, type=Path)
    arguments = parser.parse_args()
    result: FeatureBuildResult = build_feature_database(
        ROOT, arguments.risk_config.resolve(), arguments.peer_config.resolve(), arguments.quality_config.resolve()
    )
    report_hashes: dict[str, str] = export_feature_reports(ROOT, result.database_path, arguments.risk_config.resolve())
    manifest_path: Path = ROOT / "manifests/feature_build/run_manifest.json"
    manifest: JsonObject = load_json_object(manifest_path)
    manifest["report_hashes"] = report_hashes
    write_replaceable_json(manifest_path, manifest)
    print(f"PASS database={result.database_path} sha256={result.database_sha256}")
    print(f"PASS features={result.feature_count} peer_benchmark_rows={result.peer_benchmark_rows} reports={len(report_hashes)}")


if __name__ == "__main__":
    main()
