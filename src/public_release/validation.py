"""Validate the publication-safe dashboard package and aggregate evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pandas as pd
import pyarrow.parquet as pq

from src.database.manifest import sha256_file

DEMO_FILES: Final[tuple[str, ...]] = (
    "dashboard_demo_scores.parquet", "dashboard_demo_history.parquet", "dashboard_demo_watchlist.parquet",
    "dashboard_demo_drivers.parquet", "dashboard_demo_peer_comparisons.parquet", "dashboard_demo_validation.parquet",
    "dashboard_demo_case_studies.parquet", "dashboard_demo_quality.parquet", "dashboard_demo_metadata.parquet",
    "synthetic_bank_quarter_sample.parquet",
)
EXPECTED_METRICS: Final[dict[str, float]] = {
    "average_precision": 0.148342, "baseline_average_precision": 0.000513, "roc_auc": 0.794209,
    "brier_score": 0.000604, "calibration_slope": 0.314724, "captured_failures_top_1": 10.0,
    "captured_failures_top_5": 10.0, "captured_failures_top_10": 12.0, "unique_locked_test_failures": 17.0,
    "median_top_5_lead_days": 284.0, "locked_test_access_count": 1.0,
}


class PublicReleaseValidationError(ValueError):
    """Raised when the release package violates its public contract."""


def validate_manifest(data_directory: Path) -> dict[str, object]:
    manifest_path: Path = data_directory / "SAMPLE_GENERATION_MANIFEST.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Demo manifest is missing: {manifest_path}")
    manifest: dict[str, object] = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries: object = manifest.get("files")
    if not isinstance(entries, list):
        raise PublicReleaseValidationError("Demo manifest files must be a list.")
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise PublicReleaseValidationError("Demo manifest entry must be an object.")
        filename: object = raw_entry.get("path")
        expected_hash: object = raw_entry.get("sha256")
        if not isinstance(filename, str) or not isinstance(expected_hash, str):
            raise PublicReleaseValidationError(f"Invalid demo manifest entry: {raw_entry}")
        path: Path = data_directory / filename
        if sha256_file(path) != expected_hash:
            raise PublicReleaseValidationError(f"Demo hash mismatch: {filename}")
    return manifest


def validate_synthetic_identifiers(data_directory: Path) -> int:
    scores: pd.DataFrame = pd.read_parquet(data_directory / "dashboard_demo_scores.parquet")
    if len(scores) != 800:
        raise PublicReleaseValidationError(f"Expected 800 synthetic score rows, observed {len(scores)}")
    if not scores["bank_name"].astype(str).str.fullmatch(r"Synthetic Bank \d{3}").all():
        raise PublicReleaseValidationError("Demo package contains a non-synthetic institution name.")
    if not scores["state"].eq("DEMO").all() or not scores["cert"].between(900001, 900100).all():
        raise PublicReleaseValidationError("Demo package contains an identifier outside the synthetic namespace.")
    if not scores["validation_status"].eq("DEMONSTRATION_ONLY").all():
        raise PublicReleaseValidationError("Demo score rows are missing the demonstration-only status.")
    return len(scores)


def validate_demo_schemas(data_directory: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for filename in DEMO_FILES:
        path: Path = data_directory / filename
        if not path.exists():
            raise FileNotFoundError(f"Required demo file is missing: {path}")
        parquet: pq.ParquetFile = pq.ParquetFile(path)
        if parquet.metadata.num_rows <= 0:
            raise PublicReleaseValidationError(f"Demo file has no rows: {filename}")
        counts[filename] = parquet.metadata.num_rows
    return counts


def validate_frozen_metrics(data_directory: Path) -> int:
    validation: pd.DataFrame = pd.read_parquet(data_directory / "dashboard_demo_validation.parquet")
    headline: pd.DataFrame = validation.loc[validation["section"] == "headline", ["metric_name", "y_value"]]
    observed: dict[str, float] = {str(row.metric_name): float(row.y_value) for row in headline.itertuples(index=False)}
    for metric, expected in EXPECTED_METRICS.items():
        if metric not in observed or abs(observed[metric] - expected) > 0.0000005:
            raise PublicReleaseValidationError(f"Frozen metric mismatch: metric={metric}, expected={expected}, observed={observed.get(metric)}")
    return len(EXPECTED_METRICS)


def validate_demo_package(data_directory: Path) -> dict[str, object]:
    manifest: dict[str, object] = validate_manifest(data_directory)
    counts: dict[str, int] = validate_demo_schemas(data_directory)
    score_rows: int = validate_synthetic_identifiers(data_directory)
    metric_count: int = validate_frozen_metrics(data_directory)
    return {"status": "PASS", "manifest_version": manifest["version"], "table_counts": counts, "score_rows": score_rows, "frozen_metrics": metric_count}

