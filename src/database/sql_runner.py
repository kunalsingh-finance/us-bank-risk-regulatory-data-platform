"""Ordered, hash-recorded SQL execution with strict template substitution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .manifest import sha256_file


PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


class SqlExecutionError(RuntimeError):
    """Raised when an ordered SQL file fails."""


@dataclass(frozen=True)
class SqlExecution:
    execution_order: int
    sql_file: str
    sql_sha256: str


def render_sql(content: str, substitutions: dict[str, str], sql_file: str) -> str:
    required: set[str] = set(PLACEHOLDER_PATTERN.findall(content))
    missing: list[str] = sorted(required.difference(substitutions))
    if missing:
        raise SqlExecutionError(f"SQL template {sql_file} has unresolved substitutions: {missing}")
    rendered: str = content
    for name in sorted(required):
        rendered = rendered.replace(f"{{{{{name}}}}}", substitutions[name])
    unresolved: list[str] = PLACEHOLDER_PATTERN.findall(rendered)
    if unresolved:
        raise SqlExecutionError(f"SQL template {sql_file} remains unresolved: {sorted(set(unresolved))}")
    return rendered


def execute_sql_files(
    connection: duckdb.DuckDBPyConnection,
    root: Path,
    ordered_files: tuple[str, ...],
    substitutions: dict[str, str],
) -> tuple[SqlExecution, ...]:
    executions: list[SqlExecution] = []
    for order, relative_name in enumerate(ordered_files, start=1):
        path: Path = root / relative_name
        if not path.exists():
            raise SqlExecutionError(f"Ordered SQL file does not exist: {path}")
        content: str = path.read_text(encoding="utf-8")
        rendered: str = render_sql(content, substitutions, relative_name)
        try:
            statements: list[duckdb.Statement] = connection.extract_statements(rendered)
            for statement_index, statement in enumerate(statements, start=1):
                try:
                    connection.execute(statement)
                except duckdb.Error as error:
                    raise SqlExecutionError(
                        f"SQL statement failed: order={order}, file={relative_name}, "
                        f"statement={statement_index}, error={error}"
                    ) from error
        except duckdb.Error as error:
            raise SqlExecutionError(
                f"SQL execution failed: order={order}, file={relative_name}, error={error}"
            ) from error
        executions.append(
            SqlExecution(
                execution_order=order,
                sql_file=relative_name,
                sql_sha256=sha256_file(path),
            )
        )
    return tuple(executions)
