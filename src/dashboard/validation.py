"""Presentation table and immutable-input controls."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from src.database.manifest import JsonObject, sha256_file
from src.models.config import require_string


REQUIRED_METADATA_COLUMNS: frozenset[str] = frozenset({
    "dashboard_build_run_id", "dashboard_configuration_hash", "frozen_model_version",
    "prediction_source_hash", "source_lineage", "build_timestamp", "validation_status",
})


class DashboardValidationError(ValueError):
    """Raised when a dashboard contract or immutable input fails."""


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required dashboard artifact is missing: {path}")


def validate_parquet_schema(path: Path, required_columns: frozenset[str]) -> int:
    require_file(path)
    parquet: pq.ParquetFile = pq.ParquetFile(path)
    columns: set[str] = set(parquet.schema_arrow.names)
    missing: set[str] = required_columns.difference(columns)
    if missing:
        raise DashboardValidationError(f"Parquet schema mismatch: path={path}, missing={sorted(missing)}")
    return parquet.metadata.num_rows


def verify_immutable_inputs(root: Path, config: JsonObject) -> dict[str, str]:
    paths: tuple[tuple[str, Path], ...] = (
        ("phase3_database_sha256", root / "database/bank_risk_features.duckdb"),
        ("phase4_database_sha256", root / "database/bank_risk_labels.duckdb"),
        ("phase5_model_database_sha256", root / "database/bank_risk_models.duckdb"),
        ("model_artifact_sha256", root / require_string(config, "model_artifact_path")),
    )
    observed: dict[str, str] = {}
    for key, path in paths:
        require_file(path)
        digest: str = sha256_file(path)
        expected: str = require_string(config, key)
        if digest != expected:
            raise DashboardValidationError(f"Immutable input mismatch: key={key}, expected={expected}, observed={digest}, path={path}")
        observed[key] = digest
    return observed
