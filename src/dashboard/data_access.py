"""Read-only, filter-before-materialization access to prepared Parquet tables."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pyarrow.parquet as pq

from .validation import require_file


def parquet_sql(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def query_parquet(path: Path, columns: tuple[str, ...], where_sql: str, parameters: tuple[object, ...]) -> pd.DataFrame:
    require_file(path)
    selected: str = ",".join(f'"{column}"' for column in columns)
    query: str = f"SELECT {selected} FROM read_parquet('{parquet_sql(path)}')"
    if where_sql:
        query += f" WHERE {where_sql}"
    connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:", read_only=False)
    try:
        return connection.execute(query, list(parameters)).fetch_df()
    finally:
        connection.close()


def distinct_values(path: Path, column: str) -> list[object]:
    require_file(path)
    connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
    try:
        values: list[tuple[object]] = connection.execute(
            f"SELECT DISTINCT \"{column}\" FROM read_parquet('{parquet_sql(path)}') WHERE \"{column}\" IS NOT NULL ORDER BY 1"
        ).fetchall()
        return [value[0] for value in values]
    finally:
        connection.close()


def latest_reporting_date(path: Path) -> pd.Timestamp:
    require_file(path)
    connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
    try:
        value: object = connection.execute(f"SELECT MAX(reporting_date) FROM read_parquet('{parquet_sql(path)}')").fetchone()[0]
        return pd.Timestamp(value)
    finally:
        connection.close()


def parquet_columns(path: Path) -> tuple[str, ...]:
    require_file(path)
    return tuple(pq.read_schema(path).names)
