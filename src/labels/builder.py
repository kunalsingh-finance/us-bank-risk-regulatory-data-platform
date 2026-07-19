"""Transactional builder for the standalone Phase 4 label database."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from src.database.manifest import JsonObject, sha256_file, write_replaceable_json
from src.database.sql_runner import SqlExecution, execute_sql_files

from .manifest import load_hashed_configuration, require_int, require_string, require_string_list
from .validator import LabelValidationResult, validate_label_database


class LabelBuildError(RuntimeError):
    """Raised when the Phase 4 transactional build fails."""


@dataclass(frozen=True)
class LabelBuildResult:
    database_path: Path
    database_sha256: str
    label_build_run_id: str
    label_configuration_hash: str
    distress_configuration_hash: str
    validations: tuple[LabelValidationResult, ...]
    sql_executions: tuple[SqlExecution, ...]


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def require_float(config: JsonObject, key: str) -> float:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LabelBuildError(f"Expected numeric {key}; received {value!r}")
    return float(value)


def build_label_database(
    root: Path,
    label_config_path: Path,
    distress_config_path: Path,
) -> LabelBuildResult:
    labels: JsonObject = load_hashed_configuration(label_config_path)
    distress: JsonObject = load_hashed_configuration(distress_config_path)
    phase2_path: Path = (root / require_string(labels, "phase2_database")).resolve()
    phase3_path: Path = (root / require_string(labels, "phase3_database")).resolve()
    output_path: Path = (root / require_string(labels, "output_database")).resolve()
    for path in (phase2_path, phase3_path, output_path):
        if root.resolve() not in path.parents:
            raise LabelBuildError(f"Configured path escapes project root: {path}")
    for path, hash_key in ((phase2_path, "phase2_database_sha256"), (phase3_path, "phase3_database_sha256")):
        if not path.exists():
            raise LabelBuildError(f"Immutable input database is missing: {path}")
        expected_hash: str = require_string(labels, hash_key)
        observed_hash: str = sha256_file(path)
        if expected_hash != observed_hash:
            raise LabelBuildError(
                f"Immutable input hash mismatch: path={path}, expected={expected_hash}, observed={observed_hash}"
            )
    protocol_path: Path = (root / require_string(labels, "protocol_path")).resolve()
    if sha256_file(protocol_path) != require_string(labels, "protocol_sha256"):
        raise LabelBuildError("Frozen label protocol hash mismatch")
    temporary_path: Path = output_path.with_name(
        f".{output_path.stem}.{require_string(labels, 'run_id')}.tmp.duckdb"
    )
    if temporary_path.exists():
        temporary_path.unlink()
    substitutions: dict[str, str] = {
        "phase2_database_path": sql_path(phase2_path),
        "phase3_database_path": sql_path(phase3_path),
        "phase2_database_sha256": require_string(labels, "phase2_database_sha256"),
        "phase3_database_sha256": require_string(labels, "phase3_database_sha256"),
        "label_configuration_hash": require_string(labels, "configuration_hash"),
        "distress_configuration_hash": require_string(distress, "configuration_hash"),
        "protocol_sha256": require_string(labels, "protocol_sha256"),
        "label_build_run_id": require_string(labels, "run_id"),
        "build_timestamp": require_string(labels, "build_timestamp"),
        "panel_start_date": require_string(labels, "panel_start_date"),
        "surveillance_end_date": require_string(labels, "event_surveillance_end_date"),
        "minimum_history_observations": str(require_int(labels, "minimum_history_observations")),
        "minimum_distress_categories": str(require_int(distress, "minimum_category_count")),
        "severe_equity_threshold": str(require_float(distress, "capital_severe_equity_to_assets_max")),
        "severe_capital_change_threshold": str(require_float(distress, "capital_severe_yoy_change_max")),
        "capital_evidence_level_threshold": str(require_float(distress, "capital_evidence_equity_to_assets_max")),
        "capital_evidence_change_threshold": str(require_float(distress, "capital_evidence_yoy_change_max")),
        "asset_quality_level_threshold": str(require_float(distress, "asset_quality_noncurrent_ratio_min")),
        "asset_quality_change_threshold": str(require_float(distress, "asset_quality_yoy_change_min")),
        "earnings_roa_threshold": str(require_float(distress, "earnings_roa_max")),
        "earnings_loss_threshold": str(require_int(distress, "earnings_minimum_consecutive_losses")),
        "deposit_outflow_threshold": str(require_float(distress, "liquidity_deposit_outflow_min")),
        "loans_to_deposits_threshold": str(require_float(distress, "liquidity_loans_to_deposits_min")),
        "fhlb_threshold": str(require_float(distress, "liquidity_fhlb_to_assets_min")),
        "expected_rows": str(require_int(labels, "expected_rows")),
    }
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(temporary_path))
    executions: tuple[SqlExecution, ...] = ()
    validations: tuple[LabelValidationResult, ...] = ()
    try:
        connection.execute("BEGIN TRANSACTION")
        executions = execute_sql_files(
            connection, root, require_string_list(labels, "sql_execution_order"), substitutions
        )
        connection.execute(
            "INSERT INTO audit.label_build_runs VALUES (?,?::TIMESTAMP,?,?,?,?,?,'PASS')",
            [require_string(labels, "run_id"), require_string(labels, "build_timestamp"),
             require_string(labels, "configuration_hash"), require_string(distress, "configuration_hash"),
             require_string(labels, "protocol_sha256"), require_string(labels, "phase2_database_sha256"),
             require_string(labels, "phase3_database_sha256")],
        )
        for execution in executions:
            connection.execute(
                "INSERT INTO audit.label_sql_execution_log VALUES (?,?,?,?)",
                [execution.execution_order, execution.sql_file, execution.sql_sha256, require_string(labels, "run_id")],
            )
        validations = validate_label_database(connection, require_int(labels, "expected_rows"))
        connection.execute("COMMIT")
    except (duckdb.Error, OSError, ValueError, RuntimeError) as error:
        try:
            connection.execute("ROLLBACK")
        except duckdb.Error:
            pass
        connection.close()
        if temporary_path.exists():
            temporary_path.unlink()
        write_replaceable_json(root / "manifests/label_build/run_manifest.json", {
            "status": "FAIL", "label_build_run_id": require_string(labels, "run_id"),
            "error_type": type(error).__name__, "error": str(error),
        })
        raise LabelBuildError(f"Transactional label build failed: {error}") from error
    connection.close()
    os.replace(temporary_path, output_path)
    database_hash: str = sha256_file(output_path)
    manifest: JsonObject = {
        "status": "PASS", "label_build_run_id": require_string(labels, "run_id"),
        "build_timestamp": require_string(labels, "build_timestamp"),
        "label_configuration_hash": require_string(labels, "configuration_hash"),
        "distress_configuration_hash": require_string(distress, "configuration_hash"),
        "protocol_sha256": require_string(labels, "protocol_sha256"),
        "phase2_database_sha256": require_string(labels, "phase2_database_sha256"),
        "phase3_database_sha256": require_string(labels, "phase3_database_sha256"),
        "output_database_sha256": database_hash,
        "label_rows": require_int(labels, "expected_rows"),
        "sql_executions": [asdict(item) for item in executions],
        "validations": [asdict(item) for item in validations],
    }
    write_replaceable_json(root / "manifests/label_build/run_manifest.json", manifest)
    return LabelBuildResult(
        output_path, database_hash, require_string(labels, "run_id"),
        require_string(labels, "configuration_hash"), require_string(distress, "configuration_hash"),
        validations, executions,
    )
