"""Validate the completed Phase 5 model experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import sha256_file  # noqa: E402
from src.models.config import load_hashed_config  # noqa: E402


def main() -> None:
    protocol = load_hashed_config(ROOT / "configs/experiment_protocol.yaml")
    if sha256_file(ROOT / "database/bank_risk_features.duckdb") != protocol["phase3_database_sha256"]:
        raise ValueError("Phase 3 database hash changed")
    if sha256_file(ROOT / "database/bank_risk_labels.duckdb") != protocol["phase4_database_sha256"]:
        raise ValueError("Phase 4 database hash changed")
    access: pd.DataFrame = pd.read_csv(ROOT / "reports/locked_test_access_log.csv")
    if int((access["status"] == "COMPLETED").sum()) != 1:
        raise ValueError("Exactly one completed locked-test access is required")
    connection = duckdb.connect(str(ROOT / "database/bank_risk_models.duckdb"), read_only=True)
    duplicates: int = int(connection.execute("SELECT COUNT(*) FROM (SELECT outcome_name,cert,reporting_date,COUNT(*) n FROM modeling.locked_test_predictions GROUP BY 1,2,3 HAVING n>1)").fetchone()[0])
    outcomes: int = int(connection.execute("SELECT COUNT(DISTINCT outcome_name) FROM modeling.locked_test_predictions").fetchone()[0])
    connection.close()
    if duplicates != 0 or outcomes != 3:
        raise ValueError(f"Locked prediction control failed: duplicates={duplicates}, outcomes={outcomes}")
    manifest = json.loads((ROOT / "manifests/model_experiment/pre_test_selection_manifest.json").read_text(encoding="utf-8"))
    if manifest["protocol_hash"] != protocol["configuration_hash"]:
        raise ValueError("Pre-test and protocol hashes differ")
    print("PASS phase5 locked_accesses=1 immutable_inputs=PASS outcomes=3")


if __name__ == "__main__":
    main()
