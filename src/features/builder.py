"""Transactional builder for the standalone Phase 3 DuckDB feature database."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from src.database.manifest import JsonObject, sha256_file, write_replaceable_json
from src.database.sql_runner import SqlExecution, execute_sql_files

from .manifest import load_hashed_configuration, require_int, require_string, require_string_list
from .validator import FeatureValidationResult, validate_feature_database


class FeatureBuildError(RuntimeError):
    """Raised when the Phase 3 transactional feature build fails."""


@dataclass(frozen=True)
class FeatureBuildResult:
    database_path: Path
    database_sha256: str
    feature_build_run_id: str
    risk_configuration_hash: str
    peer_configuration_hash: str
    quality_configuration_hash: str
    feature_count: int
    peer_benchmark_rows: int
    validations: tuple[FeatureValidationResult, ...]
    sql_executions: tuple[SqlExecution, ...]


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def feature_names(config: JsonObject) -> tuple[str, ...]:
    raw_features: object = config.get("features")
    if not isinstance(raw_features, list):
        raise FeatureBuildError("risk_features.yaml features must be an array")
    names: list[str] = []
    for entry in raw_features:
        if not isinstance(entry, dict) or not isinstance(entry.get("feature_name"), str):
            raise FeatureBuildError(f"Invalid feature configuration entry: {entry!r}")
        names.append(str(entry["feature_name"]))
    if len(names) != len(set(names)):
        raise FeatureBuildError("Feature names must be unique")
    return tuple(names)


def insert_feature_inventory(
    connection: duckdb.DuckDBPyConnection,
    risk_config: JsonObject,
) -> None:
    connection.execute(
        """CREATE TABLE audit.feature_inventory (
               feature_name VARCHAR PRIMARY KEY, financial_category VARCHAR, formula VARCHAR,
               numerator VARCHAR, denominator VARCHAR, units VARCHAR, direction_of_risk VARCHAR,
               source_type VARCHAR, peer_benchmark_status BOOLEAN, known_limitation VARCHAR
           )"""
    )
    raw_features: object = risk_config["features"]
    if not isinstance(raw_features, list):
        raise FeatureBuildError("features must be a list")
    for item in raw_features:
        if not isinstance(item, dict):
            raise FeatureBuildError(f"Invalid feature inventory item: {item!r}")
        connection.execute(
            "INSERT INTO audit.feature_inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                item["feature_name"], item["financial_category"], item["formula"], item["numerator"],
                item["denominator"], item["units"], item["direction_of_risk"],
                item["whether_source_reported_or_derived"], item["peer_group_requirement"] != "None",
                item["known_limitation"],
            ],
        )


def build_feature_database(
    root: Path,
    risk_config_path: Path,
    peer_config_path: Path,
    quality_config_path: Path,
) -> FeatureBuildResult:
    risk: JsonObject = load_hashed_configuration(risk_config_path)
    peer: JsonObject = load_hashed_configuration(peer_config_path)
    quality: JsonObject = load_hashed_configuration(quality_config_path)
    input_path: Path = (root / require_string(risk, "input_database")).resolve()
    output_path: Path = (root / require_string(risk, "output_database")).resolve()
    if root.resolve() not in input_path.parents or root.resolve() not in output_path.parents:
        raise FeatureBuildError("Configured database path escapes project root")
    if not input_path.exists():
        raise FeatureBuildError(f"Phase 2 input database is missing: {input_path}")
    observed_input_hash: str = sha256_file(input_path)
    expected_input_hash: str = require_string(risk, "input_database_sha256")
    if observed_input_hash != expected_input_hash:
        raise FeatureBuildError(
            f"Immutable Phase 2 database hash mismatch: expected={expected_input_hash}, observed={observed_input_hash}"
        )
    temporary_path: Path = output_path.with_name(f".{output_path.stem}.{require_string(risk, 'run_id')}.tmp.duckdb")
    if temporary_path.exists():
        temporary_path.unlink()
    substitutions: dict[str, str] = {
        "input_database_path": sql_path(input_path),
        "input_database_sha256": expected_input_hash,
        "feature_build_run_id": require_string(risk, "run_id"),
        "build_timestamp": require_string(risk, "build_timestamp"),
        "risk_configuration_hash": require_string(risk, "configuration_hash"),
        "peer_configuration_hash": require_string(peer, "configuration_hash"),
        "quality_configuration_hash": require_string(quality, "configuration_hash"),
    }
    connection = duckdb.connect(str(temporary_path))
    executions: tuple[SqlExecution, ...] = ()
    validations: tuple[FeatureValidationResult, ...] = ()
    names: tuple[str, ...] = feature_names(risk)
    try:
        connection.execute("BEGIN TRANSACTION")
        executions = execute_sql_files(
            connection, root, require_string_list(risk, "sql_execution_order"), substitutions
        )
        insert_feature_inventory(connection, risk)
        connection.execute(
            "INSERT INTO audit.feature_build_runs VALUES (?, ?::TIMESTAMP, ?, ?, ?, ?, 'PASS')",
            [
                require_string(risk, "run_id"), require_string(risk, "build_timestamp"),
                require_string(risk, "configuration_hash"), require_string(peer, "configuration_hash"),
                require_string(quality, "configuration_hash"), expected_input_hash,
            ],
        )
        for execution in executions:
            connection.execute(
                "INSERT INTO audit.feature_sql_execution_log VALUES (?, ?, ?, ?)",
                [execution.execution_order, execution.sql_file, execution.sql_sha256, require_string(risk, "run_id")],
            )
        validations = validate_feature_database(connection, require_int(risk, "expected_rows"), len(names))
        connection.execute("COMMIT")
    except (duckdb.Error, OSError, ValueError, RuntimeError) as error:
        try:
            connection.execute("ROLLBACK")
        except duckdb.Error:
            pass
        connection.close()
        if temporary_path.exists():
            temporary_path.unlink()
        write_replaceable_json(root / "manifests/feature_build/run_manifest.json", {
            "status": "FAIL", "feature_build_run_id": require_string(risk, "run_id"),
            "error_type": type(error).__name__, "error": str(error),
        })
        raise FeatureBuildError(f"Transactional feature build failed: {error}") from error
    peer_rows: int = connection.execute("SELECT COUNT(*) FROM core.bank_quarter_peer_benchmarks").fetchone()[0]
    connection.close()
    os.replace(temporary_path, output_path)
    database_hash: str = sha256_file(output_path)
    manifest: JsonObject = {
        "status": "PASS",
        "feature_build_run_id": require_string(risk, "run_id"),
        "build_timestamp": require_string(risk, "build_timestamp"),
        "risk_configuration_hash": require_string(risk, "configuration_hash"),
        "peer_configuration_hash": require_string(peer, "configuration_hash"),
        "quality_configuration_hash": require_string(quality, "configuration_hash"),
        "input_database_path": str(input_path.relative_to(root)).replace("\\", "/"),
        "input_database_sha256": expected_input_hash,
        "output_database_path": str(output_path.relative_to(root)).replace("\\", "/"),
        "output_database_sha256": database_hash,
        "feature_count": len(names),
        "feature_rows": require_int(risk, "expected_rows"),
        "peer_benchmark_rows": peer_rows,
        "sql_executions": [asdict(item) for item in executions],
        "validations": [asdict(item) for item in validations],
    }
    write_replaceable_json(root / "manifests/feature_build/run_manifest.json", manifest)
    return FeatureBuildResult(
        output_path, database_hash, require_string(risk, "run_id"), require_string(risk, "configuration_hash"),
        require_string(peer, "configuration_hash"), require_string(quality, "configuration_hash"),
        len(names), peer_rows, validations, executions,
    )
