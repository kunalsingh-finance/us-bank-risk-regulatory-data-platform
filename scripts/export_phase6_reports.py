"""Run the Phase 6 language scan and freeze report/code hashes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.language import scan_paths  # noqa: E402
from src.dashboard.manifest import file_inventory, write_dashboard_manifest  # noqa: E402
from src.database.manifest import JsonObject, sha256_file  # noqa: E402


def main() -> None:
    phase6_documents: tuple[str, ...] = (
        "DASHBOARD_METHODOLOGY.md", "DASHBOARD_USER_GUIDE.md", "RISK_TIER_METHODOLOGY.md",
        "ALERT_METHODOLOGY.md", "EXPLAINABILITY_METHODOLOGY.md",
        "FAILURE_CASE_STUDY_METHODOLOGY.md", "DASHBOARD_LIMITATIONS.md",
        "DASHBOARD_DATA_LINEAGE.md", "DASHBOARD_CONTROL_INVENTORY.md",
        "STREAMLIT_DEPLOYMENT_GUIDE.md", "PHASE6_COMPLETION_REPORT.md",
        "PHASE7_PUBLIC_RELEASE_READINESS.md",
    )
    scan_paths_list: tuple[Path, ...] = (
        tuple(sorted((ROOT / "dashboards").rglob("*.py")))
        + tuple(sorted((ROOT / "src/dashboard").glob("*.py")))
        + tuple(ROOT / "docs" / name for name in phase6_documents)
        + tuple(sorted((ROOT / "configs").glob("dashboard*.yaml")))
    )
    language: pd.DataFrame = scan_paths(ROOT, scan_paths_list)
    language.to_csv(ROOT / "reports/dashboard_language_scan.csv", index=False, lineterminator="\n")
    unresolved: int = int((language["status"] == "UNRESOLVED_MISLEADING_LANGUAGE").sum())
    if unresolved:
        raise ValueError(f"Dashboard language scan failed: unresolved={unresolved}")
    report_names: tuple[str, ...] = (
        "dashboard_data_reconciliation.csv", "dashboard_score_validation.csv", "dashboard_tier_distribution.csv",
        "dashboard_watchlist_validation.csv", "dashboard_driver_validation.csv", "dashboard_peer_validation.csv",
        "dashboard_chart_reconciliation.csv", "dashboard_case_studies.csv", "dashboard_language_scan.csv",
        "dashboard_quality_exceptions.csv", "dashboard_performance_benchmark.csv", "dashboard_test_summary.csv",
        "dashboard_rebuild_reproducibility.csv", "dashboard_browser_validation.csv",
    )
    missing: list[str] = [name for name in report_names if not (ROOT / "reports" / name).exists()]
    if missing:
        raise FileNotFoundError(f"Phase 6 reports missing: {missing}")
    manifest_path: Path = ROOT / "manifests/dashboard_build/run_manifest.json"
    manifest: JsonObject = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("manifest_content_hash", None)
    manifest["report_hashes"] = {name: sha256_file(ROOT / "reports" / name) for name in report_names}
    code_paths: tuple[Path, ...] = tuple(sorted((ROOT / "src/dashboard").glob("*.py"))) + tuple(sorted((ROOT / "dashboards").rglob("*.py"))) + tuple(ROOT / "scripts" / name for name in ("prepare_dashboard_configs.py", "build_dashboard_data.py", "validate_dashboard_data.py", "export_phase6_reports.py", "run_dashboard.py")) + (ROOT / ".streamlit/config.toml",)
    manifest["code_files"] = file_inventory(ROOT, code_paths)
    manifest["language_scan_unresolved"] = unresolved
    tests: pd.DataFrame = pd.read_csv(ROOT / "reports/dashboard_test_summary.csv")
    reproducibility: pd.DataFrame = pd.read_csv(ROOT / "reports/dashboard_rebuild_reproducibility.csv")
    browser_validation: pd.DataFrame = pd.read_csv(ROOT / "reports/dashboard_browser_validation.csv")
    manifest["test_results"] = "PASS" if bool((tests["status"] == "PASS").all()) else "FAIL"
    manifest["logical_rebuild_status"] = "PASS" if bool((reproducibility["status"] == "PASS").all()) else "FAIL"
    manifest["browser_visual_validation"] = "PASS" if bool((browser_validation["status"] == "PASS").all()) else "FAIL"
    write_dashboard_manifest(manifest_path, manifest)
    print(f"PASS reports={len(report_names)} language_unresolved={unresolved}")


if __name__ == "__main__":
    main()
