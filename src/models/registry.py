"""DuckDB registry writes for Phase 5 experiment artifacts."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def replace_table_from_frame(database_path: Path, table_name: str, frame: pd.DataFrame) -> None:
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path))
    try:
        connection.register("registered_frame", frame)
        connection.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM registered_frame")
        connection.unregister("registered_frame")
    finally:
        connection.close()


def append_frame(database_path: Path, table_name: str, frame: pd.DataFrame) -> None:
    if frame.empty:
        return
    connection: duckdb.DuckDBPyConnection = duckdb.connect(str(database_path))
    try:
        connection.register("registered_frame", frame)
        connection.execute(f"INSERT INTO {table_name} BY NAME SELECT * FROM registered_frame")
        connection.unregister("registered_frame")
    finally:
        connection.close()
