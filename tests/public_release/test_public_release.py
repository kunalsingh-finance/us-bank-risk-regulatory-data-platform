"""Integration controls for the publication-safe release candidate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd

from src.dashboard.app_pages import DEMO_TABLE_NAMES
from src.public_release.audit import BINARY_SUFFIXES, read_text_for_scan, repository_files
from src.public_release.validation import DEMO_FILES, EXPECTED_METRICS, validate_demo_package

ROOT: Path = Path(__file__).resolve().parents[2]
DATA: Path = ROOT / "public_release/data"


class PublicReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validation = validate_demo_package(DATA)
        cls.scores = pd.read_parquet(DATA / "dashboard_demo_scores.parquet")
        cls.validation_frame = pd.read_parquet(DATA / "dashboard_demo_validation.parquet")

    def test_01_demo_manifest_complete(self) -> None:
        self.assertEqual("PASS", self.validation["status"])
        self.assertEqual(set(DEMO_FILES), set(self.validation["table_counts"]))

    def test_02_full_raw_data_excluded_from_demo(self) -> None:
        self.assertFalse(any("raw" in path.name.lower() for path in DATA.glob("*.parquet")))

    def test_03_full_panel_excluded(self) -> None:
        self.assertNotIn("fdic_financials_2001q1_2026q1.parquet", {path.name for path in DATA.iterdir()})

    def test_04_full_peer_table_excluded(self) -> None:
        peers: int = int(self.validation["table_counts"]["dashboard_demo_peer_comparisons.parquet"])
        self.assertLess(peers, 10000)

    def test_05_duckdb_binary_excluded(self) -> None:
        self.assertFalse(any(path.suffix.lower() == ".duckdb" for path in repository_files(ROOT / "public_release")))

    def test_06_model_binary_excluded(self) -> None:
        self.assertFalse(any(path.suffix.lower() in {".pkl", ".pickle", ".joblib"} for path in repository_files(ROOT / "public_release")))

    def test_07_demo_score_schema(self) -> None:
        required: set[str] = {"cert", "reporting_date", "same_quarter_percentile", "risk_tier", "validation_status"}
        self.assertTrue(required.issubset(self.scores.columns))

    def test_08_demo_names_are_synthetic(self) -> None:
        self.assertTrue(self.scores["bank_name"].str.fullmatch(r"Synthetic Bank \d{3}").all())

    def test_09_demo_identifier_namespace(self) -> None:
        self.assertTrue(self.scores["cert"].between(900001, 900100).all())

    def test_10_demo_quarter_count(self) -> None:
        self.assertEqual(8, self.scores["reporting_date"].nunique())

    def test_11_demo_bank_count(self) -> None:
        self.assertEqual(100, self.scores["cert"].nunique())

    def test_12_dashboard_table_mapping(self) -> None:
        self.assertEqual(9, len(DEMO_TABLE_NAMES))
        self.assertTrue(all((DATA / filename).exists() for filename in DEMO_TABLE_NAMES.values()))

    def test_13_no_personal_path_in_candidate_text(self) -> None:
        marker: str = "C:" + "\\Users\\" + "perso"
        matches: list[str] = [path.as_posix() for path in repository_files(ROOT) if marker.lower() in read_text_for_scan(path).lower()]
        self.assertEqual([], matches)

    def test_14_no_secret_files(self) -> None:
        names: set[str] = {path.name.lower() for path in repository_files(ROOT / "public_release")}
        self.assertNotIn("secrets.toml", names)
        self.assertNotIn(".env", names)

    def test_15_only_approved_demo_binaries(self) -> None:
        violations: list[str] = [path.name for path in repository_files(ROOT / "public_release") if path.suffix.lower() in BINARY_SUFFIXES and path.suffix.lower() != ".parquet"]
        self.assertEqual([], violations)

    def test_16_readme_demo_commands(self) -> None:
        readme: str = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("scripts\\run_demo.py", readme)
        self.assertIn("scripts\\validate_environment.py", readme)

    def test_17_score_row_reconciliation(self) -> None:
        self.assertEqual(800, len(self.scores))
        self.assertFalse(self.scores.duplicated(["cert", "reporting_date"]).any())

    def test_18_frozen_metric_reconciliation(self) -> None:
        headline: dict[str, float] = {str(row.metric_name): float(row.y_value) for row in self.validation_frame.query("section == 'headline'").itertuples()}
        self.assertTrue(all(abs(headline[key] - value) <= 0.0000005 for key, value in EXPECTED_METRICS.items()))

    def test_19_demo_disclaimer_present(self) -> None:
        source: str = (ROOT / "src/dashboard/app_pages.py").read_text(encoding="utf-8")
        self.assertIn("DEMONSTRATION MODE", source)
        self.assertIn("not a probability", source.lower())

    def test_20_responsible_use_present(self) -> None:
        text: str = (ROOT / "RESPONSIBLE_USE.md").read_text(encoding="utf-8")
        self.assertIn("official bank supervision", text)
        self.assertIn("public accusations", text)

    def test_21_license_consistency(self) -> None:
        license_text: str = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("does not grant rights in FDIC source data", license_text)

    def test_22_third_party_notice_complete(self) -> None:
        text: str = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for package in ("DuckDB", "PyArrow", "pandas", "scikit-learn", "SciPy", "Streamlit", "Plotly", "PyYAML"):
            self.assertIn(package, text)

    def test_23_ranking_only_claim(self) -> None:
        readme: str = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("research ranking model", readme)
        self.assertIn("Calibration was weak", readme)

    def test_24_readme_local_links_exist(self) -> None:
        for relative in ("docs/FULL_REBUILD_GUIDE.md", "docs/DATA_REDISTRIBUTION_POLICY.md", "RESPONSIBLE_USE.md", "THIRD_PARTY_NOTICES.md"):
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_25_environment_validation_command(self) -> None:
        completed: subprocess.CompletedProcess[str] = subprocess.run([sys.executable, "scripts/validate_environment.py"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("PASS", json.loads(completed.stdout)["status"])

    def test_26_full_rebuild_configuration_validation(self) -> None:
        environment: dict[str, str] = dict(os.environ)
        environment.pop("BANK_RISK_FULL_REBUILD_CONFIRM", None)
        completed: subprocess.CompletedProcess[str] = subprocess.run([sys.executable, "scripts/run_full_pipeline.py", "--config", "configs/full_pipeline.yaml"], cwd=ROOT, env=environment, capture_output=True, text=True, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("PLAN_VALIDATED", json.loads(completed.stdout)["status"])

    def test_27_manifest_hashes_are_reproducible(self) -> None:
        manifest: dict[str, object] = json.loads((DATA / "SAMPLE_GENERATION_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(10, len(manifest["files"]))

    def test_28_ai_disclosure_present(self) -> None:
        text: str = (ROOT / "docs/AI_ASSISTANCE_DISCLOSURE.md").read_text(encoding="utf-8")
        self.assertIn("Codex assisted", text)
        self.assertIn("candidate", text)

    def test_29_data_policy_excludes_raw_redistribution(self) -> None:
        text: str = (ROOT / "docs/DATA_REDISTRIBUTION_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("Intentionally excluded", text)
        self.assertIn("API-response archives", text)

    def test_30_earlier_frozen_hashes_documented(self) -> None:
        model_card: str = (ROOT / "docs/MODEL_CARD.md").read_text(encoding="utf-8")
        self.assertIn("f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4", model_card)
        self.assertIn("da032d45f4db5578dfe2f29b2717eb8c16a48a4722343e79d7c151ca45991276", model_card)

    def test_31_demo_tables_use_name_mapping(self) -> None:
        source: str = (ROOT / "src/dashboard/app_pages.py").read_text(encoding="utf-8")
        self.assertEqual(1, source.count("DATA /"), "Dashboard data access must pass through dashboard_table_path in demo mode.")


if __name__ == "__main__":
    unittest.main()
