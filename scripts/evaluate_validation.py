"""Validate the frozen Phase 5 validation-selection evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]


def main() -> None:
    comparison: pd.DataFrame = pd.read_csv(ROOT / "reports/validation_model_comparison.csv")
    selection: dict[str, object] = json.loads((ROOT / "manifests/model_experiment/validation_selection_manifest.json").read_text(encoding="utf-8"))
    selected: str = str(selection["selected_primary_model"])
    expected: str = str(comparison.sort_values(["average_precision", "brier_score", "model_id"], ascending=[False, True, True]).iloc[0]["model_id"])
    if selected != expected:
        raise ValueError(f"Validation selection mismatch: selected={selected}, expected={expected}")
    if bool(selection["locked_test_accessed"]):
        raise ValueError("Validation manifest unexpectedly records locked-test access")
    print(f"PASS validation_selection={selected} candidates={len(comparison)}")


if __name__ == "__main__":
    main()
