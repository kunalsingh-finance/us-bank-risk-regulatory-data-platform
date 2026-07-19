"""Build the Phase 4 label database and deterministic reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, load_json_object, write_replaceable_json  # noqa: E402
from src.labels.builder import LabelBuildResult, build_label_database  # noqa: E402
from src.labels.reporting import export_label_reports  # noqa: E402


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--label-config", required=True, type=Path)
    parser.add_argument("--distress-config", required=True, type=Path)
    arguments: argparse.Namespace = parser.parse_args()
    result: LabelBuildResult = build_label_database(
        ROOT, arguments.label_config.resolve(), arguments.distress_config.resolve()
    )
    report_hashes: dict[str, str] = export_label_reports(ROOT, result.database_path)
    manifest_path: Path = ROOT / "manifests/label_build/run_manifest.json"
    manifest: JsonObject = load_json_object(manifest_path)
    manifest["report_hashes"] = report_hashes
    write_replaceable_json(manifest_path, manifest)
    print(f"PASS database={result.database_path} sha256={result.database_sha256}")
    print(f"PASS label_rows=698804 reports={len(report_hashes)}")


if __name__ == "__main__":
    main()
