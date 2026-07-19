"""Confirm secondary outcomes were evaluated in the single governed test access."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]


def main() -> None:
    access: pd.DataFrame = pd.read_csv(ROOT / "reports/locked_test_access_log.csv")
    if int((access["status"] == "COMPLETED").sum()) != 1:
        raise ValueError("Secondary results require exactly one completed locked-test access")
    results: pd.DataFrame = pd.read_csv(ROOT / "reports/secondary_outcome_results.csv")
    expected: set[str] = {"failure_8q", "deterioration_4q"}
    if set(results["outcome_name"]) != expected:
        raise ValueError(f"Secondary outcome mismatch: observed={set(results['outcome_name'])}")
    print("PASS secondary_outcomes=failure_8q,deterioration_4q")


if __name__ == "__main__":
    main()
