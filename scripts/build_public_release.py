"""Build deterministic publication-safe demonstration datasets."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.public_release.demo_data import build_demo_package  # noqa: E402

SAFE_AGGREGATE_REPORTS: tuple[str, ...] = (
    "candidate_model_results.csv",
    "dashboard_chart_reconciliation.csv",
    "dashboard_data_reconciliation.csv",
    "dashboard_language_scan.csv",
    "locked_test_access_log.csv",
    "locked_test_metrics.csv",
    "model_feature_importance.csv",
    "model_performance_by_asset_band.csv",
    "model_performance_by_bank_class.csv",
    "model_performance_by_period.csv",
    "model_uncertainty_intervals.csv",
    "validation_model_comparison.csv",
)


def copy_aggregate_reports(root: Path, output: Path) -> int:
    report_directory: Path = output.parent / "reports"
    report_directory.mkdir(parents=True, exist_ok=True)
    for filename in SAFE_AGGREGATE_REPORTS:
        source: Path = root / "reports" / filename
        if not source.exists():
            raise FileNotFoundError(f"Publication-safe aggregate report is missing: {source}")
        shutil.copyfile(source, report_directory / filename)
    return len(SAFE_AGGREGATE_REPORTS)


def parse_arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Build publication-safe synthetic dashboard data.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bank-count", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    arguments: argparse.Namespace = parse_arguments()
    output: Path = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    manifest: dict[str, object] = build_demo_package(ROOT, output, int(arguments.bank_count))
    report_count: int = copy_aggregate_reports(ROOT, output)
    print(json.dumps({"status": "PASS", "output": output.as_posix(), "data_files": len(manifest["files"]), "aggregate_reports": report_count}, sort_keys=True))


if __name__ == "__main__":
    main()
