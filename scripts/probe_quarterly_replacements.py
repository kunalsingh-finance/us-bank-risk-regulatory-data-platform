"""Validate quarterly replacements for YTD Phase 0 financial fields."""

from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.downloader import download_query  # noqa: E402
from src.ingestion.fdic_client import FdicClient, FdicClientConfig, FinancialsQuery  # noqa: E402
from src.ingestion.schema import Record, Scalar  # noqa: E402


FIELDS: tuple[str, ...] = (
    "CERT",
    "REPDTE",
    "NETINC",
    "NETINCQ",
    "NIM",
    "NIMQ",
    "NIMY",
    "NIMYQ",
    "NONII",
    "NONIIQ",
    "NONIX",
    "NONIXQ",
    "PTAXNETINC",
    "PTAXNETINCQ",
    "ROA",
    "ROAQ",
    "EEFFR",
    "EEFFQR",
    "INTEXPY",
    "INTEXPYQ",
    "NTLNLS",
    "NTLNLSQ",
)


def load_object(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return {str(key): item for key, item in value.items()}


def number(value: Scalar) -> float | None:
    if value is None or isinstance(value, bool) or str(value).strip().lower() in {"", "null"}:
        return None
    try:
        parsed: float = float(str(value))
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def stats(records: list[Record], field: str) -> dict[str, object]:
    values: list[float] = [value for record in records if (value := number(record.get(field))) is not None]
    total: int = len(records)
    return {
        "Non-null count": len(values),
        "Non-null percentage": 0.0 if total == 0 else 100.0 * len(values) / total,
        "Zero percentage": 0.0 if total == 0 else 100.0 * sum(value == 0 for value in values) / total,
        "Minimum": min(values) if values else "",
        "Median": statistics.median(values) if values else "",
        "Maximum": max(values) if values else "",
    }


def run() -> None:
    config = load_object(ROOT / "configs" / "fdic_download_config.yaml")
    anchors = load_object(ROOT / "configs" / "anchor_quarters.yaml")
    required = frozenset(str(value) for value in config["required_fields"])
    allowed = frozenset(str(value) for value in config["allowed_unexpected_fields"])
    client = FdicClient.live(FdicClientConfig(str(config["base_url"]), int(config["timeout_seconds"]), int(config["max_attempts"]), float(config["backoff_base_seconds"]), str(config["user_agent"]), allowed, required))
    rows: list[dict[str, object]] = []
    anchor_values: object = anchors["anchors"]
    if not isinstance(anchor_values, list):
        raise ValueError("anchors must be an array")
    for anchor_value in anchor_values:
        if not isinstance(anchor_value, dict):
            raise ValueError("anchor must be an object")
        quarter: str = str(anchor_value["quarter"])
        report_date: str = str(anchor_value["report_date"])
        output_dir: Path = ROOT / "data" / "raw" / "api" / "quarterly_replacements" / quarter
        query = FinancialsQuery(f"{config['population_filter']} AND REPDTE:{report_date}", FIELDS, str(config["sort_by"]), str(config["sort_order"]), 10000, 0, str(config["format"]))
        result = download_query(client, str(config["endpoint"]), query, output_dir, output_dir / "checkpoint.json", report_date, required, allowed)
        for field in FIELDS:
            if field in {"CERT", "REPDTE"}:
                continue
            rows.append({"Field": field, "Quarter": quarter, "Row count": result.total, **stats(result.records, field)})
        print(f"{quarter}: rows={result.total}")
    report_path: Path = ROOT / "reports" / "quarterly_replacement_probe.csv"
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        columns: list[str] = ["Field", "Quarter", "Row count", "Non-null count", "Non-null percentage", "Zero percentage", "Minimum", "Median", "Maximum"]
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
