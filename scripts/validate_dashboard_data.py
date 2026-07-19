"""Validate Phase 6 presentation tables and frozen-source reconciliation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.config import load_dashboard_configs  # noqa: E402
from src.dashboard.validation import REQUIRED_METADATA_COLUMNS, DashboardValidationError, validate_parquet_schema, verify_immutable_inputs  # noqa: E402
from src.database.manifest import sha256_file  # noqa: E402


def main() -> None:
    config, _, _, _ = load_dashboard_configs(ROOT)
    verify_immutable_inputs(ROOT, config)
    manifest_path: Path = ROOT / "manifests/dashboard_build/run_manifest.json"
    manifest: dict[str, object] = json.loads(manifest_path.read_text(encoding="utf-8"))
    presentation: object = manifest.get("presentation_tables")
    if not isinstance(presentation, dict) or len(presentation) != 9:
        raise DashboardValidationError("Dashboard manifest must contain nine presentation tables")
    directory: Path = ROOT / str(config["presentation_directory"])
    for name, raw in presentation.items():
        if not isinstance(raw, dict):
            raise TypeError(f"Invalid presentation manifest entry: {name}")
        path: Path = directory / f"{name}.parquet"
        rows: int = validate_parquet_schema(path, REQUIRED_METADATA_COLUMNS)
        if rows != int(raw["rows"]) or sha256_file(path) != str(raw["sha256"]):
            raise DashboardValidationError(f"Presentation artifact mismatch: {name}")
    connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
    scores_path: str = str(directory / "bank_scores.parquet").replace("\\", "/")
    controls: tuple[int, int, int, int, int] = tuple(connection.execute(f"""SELECT COUNT(*),
        COUNT(*)-COUNT(DISTINCT (cert,reporting_date)),
        COUNT(*) FILTER(WHERE same_quarter_percentile<0 OR same_quarter_percentile>100),
        COUNT(*) FILTER(WHERE prediction_split='LOCKED_TEST' AND top_5_percent_flag),
        COUNT(*) FILTER(WHERE risk_tier='High' OR risk_tier='Highest monitored tier')
        FROM read_parquet('{scores_path}')""").fetchone())
    connection.close()
    if controls[0] != 228777 or controls[1] != 0 or controls[2] != 0 or controls[3] != 5670:
        raise DashboardValidationError(f"Score controls failed: {controls}")
    language_path: Path = ROOT / "reports/dashboard_language_scan.csv"
    if language_path.exists():
        language: pd.DataFrame = pd.read_csv(language_path)
        if int((language["status"] == "UNRESOLVED_MISLEADING_LANGUAGE").sum()) != 0:
            raise DashboardValidationError("Dashboard language scan contains unresolved findings")
    print(f"PASS tables=9 score_rows={controls[0]} locked_top5={controls[3]} immutable_inputs=PASS")


if __name__ == "__main__":
    main()
