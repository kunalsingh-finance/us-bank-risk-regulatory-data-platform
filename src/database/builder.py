"""Transactional, temporary-file DuckDB builder for Phase 2."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from .manifest import (
    JsonObject,
    ManifestError,
    configuration_hash,
    load_json_object,
    sha256_file,
    write_replaceable_json,
)
from .sql_runner import SqlExecution, execute_sql_files
from .validator import ValidationResult, validate_database


class DatabaseBuildError(RuntimeError):
    """Raised when the database cannot be built and validated transactionally."""


@dataclass(frozen=True)
class SourceFile:
    name: str
    path: Path
    sha256: str
    expected_rows: int


@dataclass(frozen=True)
class BuildResult:
    database_path: Path
    database_sha256: str
    configuration_hash: str
    build_run_id: str
    validations: tuple[ValidationResult, ...]
    sql_executions: tuple[SqlExecution, ...]
    table_rows: dict[str, int]


def require_string(config: JsonObject, key: str) -> str:
    value: object = config.get(key)
    if not isinstance(value, str):
        raise ManifestError(f"Expected string configuration value {key}; received {value!r}")
    return value


def require_int(config: JsonObject, key: str) -> int:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(f"Expected integer configuration value {key}; received {value!r}")
    return value


def require_object(config: JsonObject, key: str) -> JsonObject:
    value: object = config.get(key)
    if not isinstance(value, dict):
        raise ManifestError(f"Expected object configuration value {key}; received {value!r}")
    return {str(item_key): item_value for item_key, item_value in value.items()}


def require_string_list(config: JsonObject, key: str) -> tuple[str, ...]:
    value: object = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ManifestError(f"Expected string array configuration value {key}; received {value!r}")
    return tuple(str(item) for item in value)


def parse_sources(root: Path, config: JsonObject) -> tuple[SourceFile, ...]:
    raw_sources: object = config.get("input_sources")
    if not isinstance(raw_sources, list):
        raise ManifestError("input_sources must be an array")
    sources: list[SourceFile] = []
    for entry in raw_sources:
        if not isinstance(entry, dict):
            raise ManifestError(f"Input source entry must be an object: {entry!r}")
        name: object = entry.get("name")
        relative_path: object = entry.get("path")
        expected_hash: object = entry.get("sha256")
        expected_rows: object = entry.get("expected_rows")
        if not isinstance(name, str) or not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            raise ManifestError(f"Input source entry has invalid strings: {entry!r}")
        if isinstance(expected_rows, bool) or not isinstance(expected_rows, int):
            raise ManifestError(f"Input source expected_rows must be integer: {entry!r}")
        path: Path = (root / relative_path).resolve()
        if root.resolve() not in path.parents:
            raise ManifestError(f"Input source escapes project root: {relative_path}")
        sources.append(SourceFile(name, path, expected_hash, expected_rows))
    names: list[str] = [source.name for source in sources]
    if len(names) != len(set(names)):
        raise ManifestError(f"Input source names must be unique: {names}")
    return tuple(sources)


def validate_source_hashes(sources: tuple[SourceFile, ...]) -> None:
    failures: list[str] = []
    for source in sources:
        if not source.path.exists():
            failures.append(f"missing {source.name}: {source.path}")
            continue
        observed: str = sha256_file(source.path)
        if observed != source.sha256:
            failures.append(
                f"hash mismatch {source.name}: expected={source.sha256}, observed={observed}, path={source.path}"
            )
    if failures:
        raise DatabaseBuildError("Source validation failed: " + "; ".join(failures))


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def source_by_name(sources: tuple[SourceFile, ...], name: str) -> SourceFile:
    matches: list[SourceFile] = [source for source in sources if source.name == name]
    if len(matches) != 1:
        raise ManifestError(f"Expected exactly one input source named {name}; found {len(matches)}")
    return matches[0]


def build_substitutions(
    root: Path,
    config: JsonObject,
    sources: tuple[SourceFile, ...],
    config_digest: str,
) -> dict[str, str]:
    financial: SourceFile = source_by_name(sources, "financials")
    institution: SourceFile = source_by_name(sources, "institutions")
    history: SourceFile = source_by_name(sources, "history_events")
    failure: SourceFile = source_by_name(sources, "failures")
    thresholds: JsonObject = require_object(config, "validation_thresholds")
    return {
        "financials_path": sql_path(financial.path),
        "institutions_path": sql_path(institution.path),
        "history_path": sql_path(history.path),
        "failures_path": sql_path(failure.path),
        "financial_source_path": str(financial.path.relative_to(root)).replace("\\", "/"),
        "institution_source_path": str(institution.path.relative_to(root)).replace("\\", "/"),
        "history_source_path": str(history.path.relative_to(root)).replace("\\", "/"),
        "failure_source_path": str(failure.path.relative_to(root)).replace("\\", "/"),
        "financial_source_hash": financial.sha256,
        "institution_source_hash": institution.sha256,
        "history_source_hash": history.sha256,
        "failure_source_hash": failure.sha256,
        "build_run_id": require_string(config, "run_id").replace("'", "''"),
        "configuration_hash": config_digest,
        "build_timestamp": require_string(config, "build_timestamp").replace("'", "''"),
        "expected_financial_rows": str(financial.expected_rows),
        "expected_institution_rows": str(institution.expected_rows),
        "expected_history_rows": str(history.expected_rows),
        "expected_failure_rows": str(failure.expected_rows),
        "deposit_asset_multiple": str(thresholds["deposit_asset_multiple"]),
        "percentage_abs_bound": str(thresholds["percentage_abs_bound"]),
    }


def safe_temporary_path(database_path: Path, run_id: str) -> Path:
    safe_run_id: str = "".join(character for character in run_id if character.isalnum() or character in {"-", "_"})
    if not safe_run_id:
        raise ManifestError(f"Run ID does not contain a safe filename component: {run_id!r}")
    return database_path.with_name(f".{database_path.stem}.{safe_run_id}.tmp.duckdb")


def remove_owned_temporary(path: Path, expected_parent: Path) -> None:
    resolved: Path = path.resolve()
    if resolved.parent != expected_parent.resolve() or not resolved.name.startswith(".bank_risk."):
        raise DatabaseBuildError(f"Refusing to remove non-owned temporary database: {resolved}")
    if resolved.exists():
        resolved.unlink()


def insert_audit_metadata(
    connection: duckdb.DuckDBPyConnection,
    root: Path,
    config: JsonObject,
    config_digest: str,
    sources: tuple[SourceFile, ...],
    executions: tuple[SqlExecution, ...],
    table_rows: dict[str, int],
) -> None:
    run_id: str = require_string(config, "run_id")
    timestamp: str = require_string(config, "build_timestamp")
    connection.execute(
        "INSERT INTO audit.ingestion_runs VALUES (?, ?, ?, ?, ?::TIMESTAMP, 'PASS')",
        [run_id, require_string(config, "build_version"), require_string(config, "schema_version"), config_digest, timestamp],
    )
    for source in sources:
        relative_path: str = str(source.path.relative_to(root)).replace("\\", "/")
        connection.execute(
            "INSERT INTO audit.source_files VALUES (?, ?, ?, ?, ?, TRUE, ?)",
            [source.name, relative_path, source.sha256, source.expected_rows, source.expected_rows, run_id],
        )
    for execution in executions:
        connection.execute(
            "INSERT INTO audit.sql_execution_log VALUES (?, ?, ?, ?::TIMESTAMP, 'PASS')",
            [execution.execution_order, execution.sql_file, execution.sql_sha256, timestamp],
        )
    for table_name, row_count in sorted(table_rows.items()):
        distinct_keys: int | None = None
        if table_name == "core.bank_quarter_financials":
            distinct_keys = connection.execute(
                "SELECT COUNT(DISTINCT (cert, reporting_date)) FROM core.bank_quarter_financials"
            ).fetchone()[0]
        elif table_name in {"core.institutions", "core.bank_failures_reference"}:
            distinct_keys = connection.execute(f"SELECT COUNT(DISTINCT cert) FROM {table_name}").fetchone()[0]
        connection.execute(
            "INSERT INTO audit.table_build_manifest VALUES (?, ?, ?, ?, ?)",
            [table_name, row_count, distinct_keys, run_id, require_string(config, "schema_version")],
        )


def collect_table_rows(
    connection: duckdb.DuckDBPyConnection, table_names: tuple[str, ...]
) -> dict[str, int]:
    result: dict[str, int] = {}
    for table_name in table_names:
        value: object = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if not isinstance(value, int):
            raise DatabaseBuildError(f"Table row count is not integer: table={table_name}, value={value!r}")
        result[table_name] = value
    return result


def build_database(root: Path, config_path: Path) -> BuildResult:
    config: JsonObject = load_json_object(config_path)
    stored_hash: str = require_string(config, "configuration_hash")
    calculated_hash: str = configuration_hash(
        {key: value for key, value in config.items() if key != "configuration_hash"}
    )
    if stored_hash != calculated_hash:
        raise DatabaseBuildError(
            f"Database build configuration hash mismatch: stored={stored_hash}, calculated={calculated_hash}"
        )
    sources: tuple[SourceFile, ...] = parse_sources(root, config)
    validate_source_hashes(sources)
    database_path: Path = (root / require_string(config, "database_path")).resolve()
    if root.resolve() not in database_path.parents:
        raise DatabaseBuildError(f"Database path escapes project root: {database_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path = safe_temporary_path(database_path, require_string(config, "run_id"))
    remove_owned_temporary(temporary_path, database_path.parent)
    substitutions: dict[str, str] = build_substitutions(root, config, sources, calculated_hash)
    sql_files: tuple[str, ...] = require_string_list(config, "sql_execution_order")
    table_names: tuple[str, ...] = require_string_list(config, "table_list")
    connection = duckdb.connect(str(temporary_path))
    executions: tuple[SqlExecution, ...] = ()
    validations: tuple[ValidationResult, ...] = ()
    table_rows: dict[str, int] = {}
    try:
        connection.execute("BEGIN TRANSACTION")
        executions = execute_sql_files(connection, root, sql_files, substitutions)
        table_rows = collect_table_rows(connection, table_names)
        validations = validate_database(
            connection,
            source_by_name(sources, "financials").expected_rows,
            source_by_name(sources, "institutions").expected_rows,
            source_by_name(sources, "history_events").expected_rows,
            source_by_name(sources, "failures").expected_rows,
        )
        insert_audit_metadata(connection, root, config, calculated_hash, sources, executions, table_rows)
        connection.execute("COMMIT")
    except (duckdb.Error, OSError, ValueError, RuntimeError) as error:
        try:
            connection.execute("ROLLBACK")
        except duckdb.Error:
            pass
        connection.close()
        remove_owned_temporary(temporary_path, database_path.parent)
        failure_manifest: JsonObject = {
            "status": "FAIL",
            "build_run_id": require_string(config, "run_id"),
            "configuration_hash": calculated_hash,
            "error_type": type(error).__name__,
            "error": str(error),
        }
        write_replaceable_json(root / "manifests" / "database_build" / "run_manifest.json", failure_manifest)
        raise DatabaseBuildError(f"Transactional database build failed: {error}") from error
    connection.close()
    os.replace(temporary_path, database_path)
    database_digest: str = sha256_file(database_path)
    result = BuildResult(
        database_path=database_path,
        database_sha256=database_digest,
        configuration_hash=calculated_hash,
        build_run_id=require_string(config, "run_id"),
        validations=validations,
        sql_executions=executions,
        table_rows=table_rows,
    )
    manifest: JsonObject = {
        "status": "PASS",
        "build_run_id": result.build_run_id,
        "configuration_hash": result.configuration_hash,
        "database_path": str(database_path.relative_to(root)).replace("\\", "/"),
        "database_sha256": result.database_sha256,
        "input_sources": [
            {
                "name": source.name,
                "path": str(source.path.relative_to(root)).replace("\\", "/"),
                "sha256": source.sha256,
                "expected_rows": source.expected_rows,
            }
            for source in sources
        ],
        "sql_executions": [asdict(execution) for execution in executions],
        "table_rows": table_rows,
        "validations": [asdict(validation) for validation in validations],
    }
    write_replaceable_json(root / "manifests" / "database_build" / "run_manifest.json", manifest)
    return result
