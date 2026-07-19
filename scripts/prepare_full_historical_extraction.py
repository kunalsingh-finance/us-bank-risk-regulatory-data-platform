"""Freeze the exact Phase 1B extraction configuration before network access."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeAlias


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.full_history import (  # noqa: E402
    JsonObject,
    configuration_hash,
    generate_quarters,
    validate_core_contract,
)
from src.ingestion.manifest import write_json_once  # noqa: E402


JsonValue: TypeAlias = str | int | float | bool | None | list[object] | dict[str, object]
START_QUARTER: str = "2001_Q1"
END_QUARTER: str = "2026_Q1"
DOWNLOADER_VERSION: str = "phase1b-1.0.0"
SCHEMA_VERSION: str = "fdic-financials-core-v1"
NORMALIZATION_VERSION: str = "source-text-v1"


def load_object(path: Path) -> JsonObject:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration root must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def require_value(config: JsonObject, key: str, expected_type: type[object]) -> object:
    value: object = config.get(key)
    if not isinstance(value, expected_type):
        raise ValueError(
            f"Configuration value {key} must be {expected_type.__name__}; received {value!r}"
        )
    return value


def build_configuration(
    contract: JsonObject,
    download_config: JsonObject,
    start_timestamp: str,
) -> JsonObject:
    fields: tuple[str, ...] = validate_core_contract(contract)
    quarters = generate_quarters(START_QUARTER, END_QUARTER)
    run_id: str = f"phase1b-{start_timestamp.replace(':', '').replace('-', '').replace('Z', 'Z').lower()}"
    config: JsonObject = {
        "phase": "1B",
        "run_id": run_id,
        "start_timestamp": start_timestamp,
        "start_quarter": START_QUARTER,
        "end_quarter": END_QUARTER,
        "quarter_count": len(quarters),
        "quarters": [
            {"quarter": quarter.label, "report_date": quarter.report_date} for quarter in quarters
        ],
        "base_url": require_value(download_config, "base_url", str),
        "api_endpoint": require_value(download_config, "endpoint", str),
        "population_filter": require_value(download_config, "population_filter", str),
        "requested_fields": list(fields),
        "sort_order": {
            "field": require_value(download_config, "sort_by", str),
            "direction": require_value(download_config, "sort_order", str),
        },
        "page_size": require_value(download_config, "page_size", int),
        "retry_policy": {
            "max_attempts": require_value(download_config, "max_attempts", int),
            "backoff_base_seconds": require_value(
                download_config, "backoff_base_seconds", float
            ),
            "rate_limit_status": 429,
            "retry_server_errors": True,
        },
        "timeout_seconds": require_value(download_config, "timeout_seconds", int),
        "checkpoint_policy": {
            "frequency": "after_each_page",
            "resume": True,
            "completed_quarter_skip": True,
            "query_hash_binding": True,
        },
        "output_formats": ["raw_json", "jsonl", "csv", "parquet"],
        "raw_output_location": "data/raw/api/financials/<YYYY_Q#>/core_v1",
        "normalized_quarter_location": "data/interim/financials_by_quarter",
        "combined_output_location": "data/processed/ingestion_stage",
        "log_location": "logs/full_historical_extraction",
        "manifest_location": "manifests/full_historical_extraction",
        "report_location": "reports/full_historical_extraction",
        "expected_identifier_fields": ["CERT", "RSSDID", "REPDTE"],
        "required_fields": require_value(download_config, "required_fields", list),
        "allowed_unexpected_fields": require_value(
            download_config, "allowed_unexpected_fields", list
        ),
        "schema_version": SCHEMA_VERSION,
        "downloader_version": DOWNLOADER_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "randomness": "none",
        "concurrency": 1,
        "format": require_value(download_config, "format", str),
        "configuration_hash_method": (
            "SHA-256 of canonical UTF-8 JSON for this object before configuration_hash is added"
        ),
    }
    digest: str = configuration_hash(config)
    return {**config, "configuration_hash": digest}


def run() -> None:
    output_path: Path = ROOT / "configs" / "full_historical_extraction.yaml"
    if output_path.exists():
        existing: JsonObject = load_object(output_path)
        stored_hash: object = existing.pop("configuration_hash", None)
        calculated_hash: str = configuration_hash(existing)
        if stored_hash != calculated_hash:
            raise ValueError(
                f"Existing frozen configuration hash mismatch: stored={stored_hash}, "
                f"calculated={calculated_hash}"
            )
        print(f"Configuration already frozen: path={output_path}, sha256={calculated_hash}")
        return
    contract: JsonObject = load_object(ROOT / "configs" / "selected_financial_fields_v1.yaml")
    download_config: JsonObject = load_object(ROOT / "configs" / "fdic_download_config.yaml")
    timestamp: str = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    config: JsonObject = build_configuration(contract, download_config, timestamp)
    write_json_once(output_path, config)
    print(
        f"Frozen {config['quarter_count']} quarters: path={output_path}, "
        f"sha256={config['configuration_hash']}, run_id={config['run_id']}"
    )


if __name__ == "__main__":
    run()
