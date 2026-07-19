"""Freeze the validation-selected Phase 5 model before locked-test access."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, sha256_file  # noqa: E402
from src.models.config import load_hashed_config, require_string  # noqa: E402
from src.models.manifest import canonical_hash, write_manifest  # noqa: E402


def git_output(arguments: list[str]) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def export_frozen_dataset(connection: duckdb.DuckDBPyConnection, split: str, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    escaped: str = str(path).replace("\\", "/").replace("'", "''")
    connection.execute(
        f"COPY (SELECT * FROM core.model_dataset_failure_4q WHERE split_assignment='{split}' "
        f"ORDER BY reporting_date,cert) TO '{escaped}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    return sha256_file(path)


def main() -> None:
    selection_path: Path = ROOT / "manifests/model_experiment/validation_selection_manifest.json"
    if not selection_path.exists():
        raise FileNotFoundError(f"Validation selection manifest is missing: {selection_path}")
    selection: JsonObject = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("status") != "PRE_TEST_SELECTION_READY" or selection.get("locked_test_accessed") is not False:
        raise ValueError("Validation selection is not eligible for pre-test freezing")
    protocol: JsonObject = load_hashed_config(ROOT / "configs/experiment_protocol.yaml")
    if selection.get("protocol_hash") != require_string(protocol, "configuration_hash"):
        raise ValueError("Selection and protocol hashes do not match")
    access_log: Path = ROOT / "reports/locked_test_access_log.csv"
    if access_log.exists() and "COMPLETED" in access_log.read_text(encoding="utf-8"):
        raise RuntimeError("Locked test has already been completed; pre-test selection cannot be changed")
    database_path: Path = ROOT / "database/bank_risk_models.duckdb"
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path), read_only=True)
    artifact_dir: Path = ROOT / "artifacts/models/phase5"
    train_path: Path = artifact_dir / "frozen_training_dataset.parquet"
    validation_path: Path = artifact_dir / "frozen_validation_dataset.parquet"
    train_hash: str = export_frozen_dataset(connection, "TRAIN", train_path)
    validation_hash: str = export_frozen_dataset(connection, "VALIDATION", validation_path)
    counts: tuple[int, int, int, int] = tuple(connection.execute(
        "SELECT COUNT(*) FILTER(WHERE split_assignment='TRAIN'),"
        "COUNT(*) FILTER(WHERE split_assignment='TRAIN' AND outcome=1),"
        "COUNT(*) FILTER(WHERE split_assignment='VALIDATION'),"
        "COUNT(*) FILTER(WHERE split_assignment='VALIDATION' AND outcome=1) "
        "FROM core.model_dataset_failure_4q"
    ).fetchone())
    connection.close()
    code_paths: tuple[Path, ...] = tuple(sorted((ROOT / "src/models").glob("*.py"))) + tuple(
        ROOT / f"scripts/{name}" for name in (
            "freeze_experiment_protocol.py", "build_model_datasets.py", "run_training_cv.py",
            "freeze_pre_test_selection.py", "run_locked_test.py",
        ) if (ROOT / f"scripts/{name}").exists()
    )
    code_files: list[dict[str, str]] = [
        {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
        for path in code_paths
    ]
    manifest: JsonObject = {
        "status": "FROZEN_BEFORE_LOCKED_TEST",
        "frozen_at": "2026-07-18T16:00:00Z",
        "branch": git_output(["branch", "--show-current"]),
        "phase4_commit": "7f4f4aa",
        "protocol_hash": selection["protocol_hash"],
        "feature_contract_hash": require_string(protocol, "model_features_hash"),
        "split_assignment_hash": json.loads((ROOT / "manifests/model_experiment/dataset_manifest.json").read_text(encoding="utf-8"))["split_assignment_sha256"],
        "training_dataset": {"path": str(train_path.relative_to(ROOT)).replace("\\", "/"), "sha256": train_hash, "rows": counts[0], "positives": counts[1]},
        "validation_dataset": {"path": str(validation_path.relative_to(ROOT)).replace("\\", "/"), "sha256": validation_hash, "rows": counts[2], "positives": counts[3]},
        "selected_model": selection["selected_primary_model"],
        "selected_family": selection["selected_family"],
        "selected_parameters": selection["selected_parameters"],
        "selected_calibration_method": selection["selected_calibration_method"],
        "classification_threshold": selection["classification_threshold"],
        "operational_alert_budget": selection["operational_alert_budget"],
        "validation_selection_metrics": selection["validation_selection_metrics"],
        "outcome_selections": selection["outcome_selections"],
        "code_files": code_files,
        "code_contract_hash": canonical_hash({"files": code_files}),
        "locked_test_access_count": 0,
        "locked_test_accessed": False,
    }
    write_manifest(ROOT / "manifests/model_experiment/pre_test_selection_manifest.json", manifest)
    metrics: JsonObject = selection["validation_selection_metrics"]  # type: ignore[assignment]
    document: str = f"""# Pre-Test Model Selection

Status: **frozen before locked-test access**  
Protocol hash: `{manifest['protocol_hash']}`

The primary four-quarter failure model is `{manifest['selected_model']}` ({manifest['selected_family']}) with frozen parameters `{json.dumps(manifest['selected_parameters'], sort_keys=True)}`. Isotonic calibration was selected by the preregistered Brier-score rule. The probability threshold is `{manifest['classification_threshold']}` and the primary operational alert budget is the top 5% within each reporting quarter.

Validation selection PR-AUC was {float(metrics['average_precision']):.6f}, versus prevalence {float(metrics['baseline_average_precision']):.6f}. Brier score was {float(metrics['brier_score']):.6f}; calibration slope was {float(metrics['calibration_slope']):.3f}. Only 15 positives occurred in the 2017–2018 final selection window, so calibration and threshold estimates are uncertain. Isotonic calibration improved Brier score but introduced ties and reduced PR-AUC relative to the raw ranking. This limitation is frozen and will not be corrected after seeing the test.

Random forest led mean rolling-origin PR-AUC, while histogram gradient boosting led the separate 2014–2018 validation comparison. Family selection followed the frozen validation-only protocol. No locked-test outcome was accessed.

The training and validation datasets, model binaries, calibrators, feature contract, protocol, and governing code are hashed in `manifests/model_experiment/pre_test_selection_manifest.json`. Any completed test access makes this selection immutable.
"""
    (ROOT / "docs/PRE_TEST_MODEL_SELECTION.md").write_text(document, encoding="utf-8")
    print(f"PASS pre_test_manifest={canonical_hash(manifest)} model={manifest['selected_model']}")


if __name__ == "__main__":
    main()
