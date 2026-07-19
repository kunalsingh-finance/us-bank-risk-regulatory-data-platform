"""Hash the deterministic Phase 5 report inventory."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import sha256_file, write_replaceable_json  # noqa: E402


def main() -> None:
    names: tuple[str, ...] = (
        "model_dataset_reconciliation.csv", "split_diagnostics.csv", "failure_events_by_split.csv",
        "institution_overlap_by_split.csv", "cross_validation_folds.csv", "candidate_model_results.csv",
        "validation_model_comparison.csv", "validation_threshold_results.csv", "validation_calibration.csv",
        "preprocessing_audit.csv", "model_feature_importance.csv", "coefficient_stability.csv",
        "feature_direction_consistency.csv", "failure_event_capture.csv", "failure_lead_time_by_event.csv",
        "model_performance_by_period.csv", "model_performance_by_asset_band.csv",
        "model_performance_by_bank_class.csv", "model_performance_by_feature_quality.csv",
        "locked_test_metrics.csv", "locked_test_threshold_results.csv", "locked_test_calibration.csv",
        "locked_test_access_log.csv", "secondary_outcome_results.csv", "model_uncertainty_intervals.csv",
        "model_quality_exceptions.csv",
    )
    missing: list[str] = [name for name in names if not (ROOT / "reports" / name).exists()]
    if missing:
        raise FileNotFoundError(f"Phase 5 reports missing: {missing}")
    hashes: dict[str, str] = {name: sha256_file(ROOT / "reports" / name) for name in names}
    write_replaceable_json(ROOT / "manifests/model_experiment/report_hashes.json", {"status": "PASS", "report_hashes": hashes})
    print(f"PASS reports={len(hashes)}")


if __name__ == "__main__":
    main()
