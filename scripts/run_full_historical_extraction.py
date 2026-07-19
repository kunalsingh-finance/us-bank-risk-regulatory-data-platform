"""Run the frozen, sequential Phase 1B FDIC quarterly extraction."""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeAlias


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.downloader import (  # noqa: E402
    DownloadResult,
    DownloadValidationError,
    download_query,
)
from src.ingestion.fdic_client import (  # noqa: E402
    FdicClient,
    FdicClientConfig,
    FdicRetryExhaustedError,
    FinancialsQuery,
)
from src.ingestion.full_history import (  # noqa: E402
    LINEAGE_FIELDS,
    JsonObject,
    Quarter,
    QuarterValidation,
    QuarterValidationError,
    completion_marker_is_valid,
    configuration_hash,
    field_statistics,
    generate_quarters,
    lineage_csv_bytes,
    numeric_fields_from_contract,
    raw_jsonl_bytes,
    scalar_text,
    source_csv_bytes,
    utc_now_text,
    validate_core_contract,
    validate_records,
    verify_page_manifests,
    write_combined_parquet,
)
from src.ingestion.manifest import (  # noqa: E402
    canonical_json_bytes,
    sha256_file,
    write_json_once,
    write_once,
    write_replaceable_json,
)
from src.ingestion.schema import Record  # noqa: E402
from src.ingestion.schema import ResponseSchemaError  # noqa: E402


LOGGER: logging.Logger = logging.getLogger(__name__)
CsvRow: TypeAlias = dict[str, object]


class FullExtractionError(RuntimeError):
    """Raised when the frozen full extraction cannot pass its controls."""


def failure_status(error: Exception) -> str:
    message: str = str(error).lower()
    if isinstance(error, FdicRetryExhaustedError):
        return "FAIL_RETRYABLE"
    if isinstance(error, ResponseSchemaError):
        return "FAIL_SCHEMA"
    if isinstance(error, (DownloadValidationError, QuarterValidationError)):
        if "duplicate" in message:
            return "FAIL_DUPLICATE"
        if "cert" in message or "rssdid" in message or "identifier" in message:
            return "FAIL_IDENTIFIER"
        if "schema" in message or "field" in message or "null" in message:
            return "FAIL_SCHEMA"
        return "FAIL_INCOMPLETE"
    return "FAIL_UNKNOWN"


def load_object(path: Path) -> JsonObject:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FullExtractionError(f"JSON-compatible configuration must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def require_string(config: JsonObject, key: str) -> str:
    value: object = config.get(key)
    if not isinstance(value, str):
        raise FullExtractionError(f"Expected string {key}; received {value!r}")
    return value


def require_int(config: JsonObject, key: str) -> int:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise FullExtractionError(f"Expected integer {key}; received {value!r}")
    return value


def require_number(config: JsonObject, key: str) -> float:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FullExtractionError(f"Expected numeric {key}; received {value!r}")
    return float(value)


def require_string_list(config: JsonObject, key: str) -> list[str]:
    value: object = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FullExtractionError(f"Expected string array {key}; received {value!r}")
    return [str(item) for item in value]


def require_object(config: JsonObject, key: str) -> JsonObject:
    value: object = config.get(key)
    if not isinstance(value, dict):
        raise FullExtractionError(f"Expected object {key}; received {value!r}")
    return {str(item_key): item_value for item_key, item_value in value.items()}


def build_client(config: JsonObject) -> tuple[FdicClient, frozenset[str], frozenset[str]]:
    retry: JsonObject = require_object(config, "retry_policy")
    required: frozenset[str] = frozenset(require_string_list(config, "required_fields"))
    allowed: frozenset[str] = frozenset(
        require_string_list(config, "allowed_unexpected_fields")
    )
    client_config = FdicClientConfig(
        base_url=require_string(config, "base_url"),
        timeout_seconds=require_int(config, "timeout_seconds"),
        max_attempts=require_int(retry, "max_attempts"),
        backoff_base_seconds=require_number(retry, "backoff_base_seconds"),
        user_agent="bank-risk-platform-phase1b/1.0 (public-data research; no credentials)",
        allowed_unexpected_fields=allowed,
        required_fields=required,
    )
    return FdicClient.live(client_config), required, allowed


def write_csv(path: Path, rows: list[CsvRow], columns: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output.getvalue(), encoding="utf-8", newline="")
    return sha256_file(path)


def page_manifest_hashes(output_dir: Path) -> list[str]:
    hashes: list[str] = []
    for path in sorted(output_dir.glob("page_*.manifest.json")):
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("response_sha256"), str):
            raise FullExtractionError(f"Page manifest lacks response_sha256: {path}")
        hashes.append(str(payload["response_sha256"]))
    return hashes


def retry_summary(quarters: tuple[Quarter, ...]) -> tuple[int, tuple[str, ...]]:
    retry_pages: int = 0
    retry_quarters: set[str] = set()
    for quarter in quarters:
        output_dir: Path = ROOT / "data" / "raw" / "api" / "financials" / quarter.label / "core_v1"
        for path in output_dir.glob("page_*.manifest.json"):
            payload: JsonObject = load_object(path)
            attempts: object = payload.get("attempts")
            if isinstance(attempts, int) and attempts > 1:
                retry_pages += 1
                retry_quarters.add(quarter.label)
    return retry_pages, tuple(sorted(retry_quarters))


def write_quarter_artifacts(
    quarter: Quarter,
    records: list[Record],
    validation: QuarterValidation,
    statistics_rows: list[JsonObject],
    output_dir: Path,
    interim_path: Path,
    core_fields: tuple[str, ...],
    run_id: str,
    endpoint: str,
    downloader_version: str,
    normalization_version: str,
    configuration_digest: str,
    extraction_timestamp: str,
    page_count: int,
) -> JsonObject:
    raw_bytes: bytes = raw_jsonl_bytes(records, core_fields)
    raw_path: Path = output_dir / "financials.combined.jsonl"
    raw_hash: str = write_once(raw_path, raw_bytes)
    source_normalized_bytes: bytes = source_csv_bytes(records, core_fields)
    source_normalized_path: Path = output_dir / "financials.normalized.csv"
    source_normalized_hash: str = write_once(source_normalized_path, source_normalized_bytes)
    manifest_relative: str = str(
        (output_dir / "download_manifest.json").relative_to(ROOT)
    ).replace("\\", "/")
    lineage: dict[str, str] = {
        "ingestion_run_id": run_id,
        "source_endpoint": endpoint,
        "requested_quarter": quarter.label,
        "source_page_count": str(page_count),
        "source_manifest_path": manifest_relative,
        "extraction_timestamp": extraction_timestamp,
        "downloader_version": downloader_version,
        "configuration_hash": configuration_digest,
        "quarter_raw_hash": raw_hash,
        "normalization_version": normalization_version,
        "validation_status": validation.status,
    }
    interim_hash: str = write_once(
        interim_path,
        lineage_csv_bytes(records, core_fields, lineage),
    )
    returned_fields: list[str] = sorted(set().union(*(record.keys() for record in records)))
    schema: JsonObject = {
        "schema_version": "fdic-financials-core-v1",
        "source_fields": list(core_fields),
        "lineage_fields": list(LINEAGE_FIELDS),
        "returned_fields": returned_fields,
        "storage_type": "UTF-8 source text; numeric parse validated without imputation",
    }
    write_json_once(output_dir / "schema.json", schema)
    write_json_once(output_dir / "missingness.json", statistics_rows)
    write_json_once(output_dir / "duplicates.json", {"count": 0, "keys": []})
    validation_payload: JsonObject = {
        **asdict(validation),
        "quarter": quarter.label,
        "report_date": quarter.report_date,
        "page_count": page_count,
        "page_hashes": page_manifest_hashes(output_dir),
        "quarter_raw_sha256": raw_hash,
        "source_normalized_sha256": source_normalized_hash,
        "interim_normalized_sha256": interim_hash,
        "configuration_hash": configuration_digest,
        "validated_at": extraction_timestamp,
    }
    write_json_once(output_dir / "validation.json", validation_payload)
    marker: JsonObject = {
        "quarter": quarter.label,
        "configuration_hash": configuration_digest,
        "validation_status": validation.status,
        "row_count": validation.row_count,
        "page_count": page_count,
        "quarter_raw_sha256": raw_hash,
        "source_normalized_sha256": source_normalized_hash,
        "interim_normalized_sha256": interim_hash,
        "completed_at": extraction_timestamp,
    }
    write_json_once(output_dir / "quarter_complete.json", marker)
    return marker


def completed_quarter_summary(
    quarter: Quarter,
    output_dir: Path,
    interim_path: Path,
    configuration_digest: str,
) -> JsonObject:
    marker_path: Path = output_dir / "quarter_complete.json"
    if not completion_marker_is_valid(marker_path, configuration_digest):
        raise FullExtractionError(f"Quarter completion marker is invalid: {marker_path}")
    marker: JsonObject = load_object(marker_path)
    if not interim_path.exists():
        raise FullExtractionError(f"Completed quarter lacks interim normalized file: {interim_path}")
    expected_hash: object = marker.get("interim_normalized_sha256")
    observed_hash: str = sha256_file(interim_path)
    if expected_hash != observed_hash:
        raise FullExtractionError(
            f"Completed quarter normalized hash mismatch: quarter={quarter.label}, "
            f"expected={expected_hash}, observed={observed_hash}"
        )
    page_count, page_rows = verify_page_manifests(output_dir)
    if page_rows != marker.get("row_count"):
        raise FullExtractionError(
            f"Completed quarter page rows do not reconcile: quarter={quarter.label}, "
            f"page_rows={page_rows}, marker_rows={marker.get('row_count')}"
        )
    return {
        "quarter": quarter.label,
        "report_date": quarter.report_date,
        "row_count": marker["row_count"],
        "page_count": page_count,
        "validation_status": marker["validation_status"],
        "quarter_raw_sha256": marker["quarter_raw_sha256"],
        "interim_normalized_sha256": observed_hash,
        "skipped_as_complete": True,
    }


def execute_quarter(
    quarter: Quarter,
    config: JsonObject,
    client: FdicClient,
    required_fields: frozenset[str],
    allowed_unexpected_fields: frozenset[str],
    core_fields: tuple[str, ...],
    numeric_fields: frozenset[str],
) -> JsonObject:
    configuration_digest: str = require_string(config, "configuration_hash")
    output_dir: Path = ROOT / "data" / "raw" / "api" / "financials" / quarter.label / "core_v1"
    interim_path: Path = (
        ROOT / "data" / "interim" / "financials_by_quarter" / f"{quarter.label}.normalized.csv"
    )
    marker_path: Path = output_dir / "quarter_complete.json"
    if completion_marker_is_valid(marker_path, configuration_digest):
        LOGGER.info("quarter_skip_complete", extra={"quarter": quarter.label})
        return completed_quarter_summary(
            quarter, output_dir, interim_path, configuration_digest
        )
    endpoint: str = require_string(config, "api_endpoint")
    population_filter: str = require_string(config, "population_filter")
    sort_order: JsonObject = require_object(config, "sort_order")
    query = FinancialsQuery(
        filters=f"{population_filter} AND REPDTE:{quarter.report_date}",
        fields=core_fields,
        sort_by=require_string(sort_order, "field"),
        sort_order=require_string(sort_order, "direction"),
        limit=require_int(config, "page_size"),
        offset=0,
        output_format=require_string(config, "format"),
    )
    request_parameters: JsonObject = {
        "quarter": quarter.label,
        "report_date": quarter.report_date,
        "endpoint": endpoint,
        "filters": query.filters,
        "fields": list(core_fields),
        "sort_by": query.sort_by,
        "sort_order": query.sort_order,
        "limit": query.limit,
        "run_id": require_string(config, "run_id"),
        "configuration_hash": configuration_digest,
    }
    write_json_once(output_dir / "request_parameters.json", request_parameters)
    extraction_timestamp: str = utc_now_text()
    result: DownloadResult = download_query(
        client=client,
        endpoint=endpoint,
        query=query,
        output_dir=output_dir,
        checkpoint_path=output_dir / "checkpoint.json",
        expected_report_date=quarter.report_date,
        required_fields=required_fields,
        allowed_unexpected_fields=allowed_unexpected_fields,
    )
    validation: QuarterValidation = validate_records(
        result.records, quarter, core_fields, numeric_fields
    )
    statistics_rows: list[JsonObject] = field_statistics(
        result.records, core_fields, numeric_fields
    )
    partial_fields: list[str] = [
        str(row["field"])
        for row in statistics_rows
        if float(row["non_null_percentage"]) < 99.0
    ]
    if partial_fields and validation.status == "PASS":
        validation = QuarterValidation(
            **{**asdict(validation), "status": "PASS_WITH_WARNINGS"}
        )
    page_count, page_rows = verify_page_manifests(output_dir)
    if page_rows != result.total:
        raise FullExtractionError(
            f"Page manifests do not reconcile for {quarter.label}: "
            f"manifest_rows={page_rows}, API_total={result.total}"
        )
    marker: JsonObject = write_quarter_artifacts(
        quarter,
        result.records,
        validation,
        statistics_rows,
        output_dir,
        interim_path,
        core_fields,
        require_string(config, "run_id"),
        endpoint,
        require_string(config, "downloader_version"),
        require_string(config, "normalization_version"),
        configuration_digest,
        extraction_timestamp,
        page_count,
    )
    LOGGER.info(
        "quarter_complete",
        extra={
            "quarter": quarter.label,
            "rows": result.total,
            "pages": page_count,
            "status": validation.status,
        },
    )
    return {
        "quarter": quarter.label,
        "report_date": quarter.report_date,
        "row_count": result.total,
        "page_count": page_count,
        "validation_status": validation.status,
        "quarter_raw_sha256": marker["quarter_raw_sha256"],
        "interim_normalized_sha256": marker["interim_normalized_sha256"],
        "skipped_as_complete": False,
    }


def read_quarter_validation(quarter: Quarter) -> tuple[JsonObject, list[JsonObject]]:
    output_dir: Path = ROOT / "data" / "raw" / "api" / "financials" / quarter.label / "core_v1"
    validation: JsonObject = load_object(output_dir / "validation.json")
    payload: object = json.loads((output_dir / "missingness.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise FullExtractionError(f"Missingness report is malformed: quarter={quarter.label}")
    return validation, [{str(key): value for key, value in row.items()} for row in payload]


def build_reports(
    quarters: tuple[Quarter, ...],
    summaries: list[JsonObject],
    core_fields: tuple[str, ...],
) -> dict[str, str]:
    report_dir: Path = ROOT / "reports" / "full_historical_extraction"
    quarterly_rows: list[CsvRow] = []
    missingness_rows: list[CsvRow] = []
    distribution_rows: list[CsvRow] = []
    institution_rows: list[CsvRow] = []
    drift_rows: list[CsvRow] = []
    exception_rows: list[CsvRow] = []
    previous_count: int | None = None
    for quarter, summary in zip(quarters, summaries, strict=True):
        validation, stats_rows = read_quarter_validation(quarter)
        raw_dir: Path = ROOT / "data" / "raw" / "api" / "financials" / quarter.label / "core_v1"
        interim_path: Path = ROOT / "data" / "interim" / "financials_by_quarter" / f"{quarter.label}.normalized.csv"
        row_count: int = int(summary["row_count"])
        raw_size: int = sum(
            path.stat().st_size for path in raw_dir.glob("page_*.json") if not path.name.endswith(".manifest.json")
        )
        normalized_size: int = interim_path.stat().st_size
        quarterly_rows.append(
            {
                "Quarter": quarter.label,
                "Report date": quarter.report_date,
                "Institution count": row_count,
                "Unique CERT count": validation["unique_cert_count"],
                "Unique RSSDID count": validation["unique_rssdid_count"],
                "Duplicate count": validation["duplicate_count"],
                "Missing CERT count": validation["missing_cert_count"],
                "Missing RSSDID count": validation["missing_rssdid_count"],
                "Missing date count": validation["missing_date_count"],
                "Field count": len(core_fields),
                "API page count": summary["page_count"],
                "Raw file size": raw_size,
                "Normalized file size": normalized_size,
                "Validation status": summary["validation_status"],
                "Quarter raw hash": summary["quarter_raw_sha256"],
                "Normalized hash": summary["interim_normalized_sha256"],
            }
        )
        institution_rows.append(
            {
                "Quarter": quarter.label,
                "Institution count": row_count,
                "Quarter-over-quarter change": "" if previous_count is None else row_count - previous_count,
                "Quarter-over-quarter percentage": "" if previous_count in {None, 0} else 100.0 * (row_count - previous_count) / previous_count,
                "Validation status": summary["validation_status"],
            }
        )
        if previous_count is not None and previous_count > 0:
            count_change: float = 100.0 * (row_count - previous_count) / previous_count
            if abs(count_change) > 10.0:
                exception_rows.append(
                    {
                        "Quarter": quarter.label,
                        "Category": "Institution count discontinuity",
                        "Field": "CERT",
                        "Severity": "WARNING",
                        "Evidence": f"Quarter-over-quarter change {count_change:.6f}%",
                        "Status": "REVIEWED_SOURCE_PRESERVED",
                        "Action": "Retain quarter and review FDIC population/history context before Phase 2",
                    }
                )
        previous_count = row_count
        for stats in stats_rows:
            field: str = str(stats["field"])
            missingness_rows.append(
                {
                    "Quarter": quarter.label,
                    "Field": field,
                    "Row count": stats["row_count"],
                    "Non-null count": stats["non_null_count"],
                    "Non-null percentage": stats["non_null_percentage"],
                    "Zero percentage": stats["zero_percentage"],
                    "Validation status": summary["validation_status"],
                }
            )
            distribution_rows.append(
                {
                    "Quarter": quarter.label,
                    "Field": field,
                    "Minimum": stats["minimum"],
                    "Maximum": stats["maximum"],
                    "Median": stats["median"],
                    "Non-null percentage": stats["non_null_percentage"],
                    "Zero percentage": stats["zero_percentage"],
                }
            )
            if float(stats["non_null_percentage"]) < 99.0:
                exception_rows.append(
                    {
                        "Quarter": quarter.label,
                        "Category": "Historical missingness",
                        "Field": field,
                        "Severity": "WARNING",
                        "Evidence": f"non_null_percentage={float(stats['non_null_percentage']):.6f}",
                        "Status": "DOCUMENTED_SOURCE_PRESERVED",
                        "Action": "Do not impute; carry field/quarter caveat into Phase 2",
                    }
                )
    report_hashes: dict[str, str] = {}
    report_hashes["quarterly_extraction_summary.csv"] = write_csv(
        report_dir / "quarterly_extraction_summary.csv",
        quarterly_rows,
        ("Quarter", "Report date", "Institution count", "Unique CERT count", "Unique RSSDID count", "Duplicate count", "Missing CERT count", "Missing RSSDID count", "Missing date count", "Field count", "API page count", "Raw file size", "Normalized file size", "Validation status", "Quarter raw hash", "Normalized hash"),
    )
    report_hashes["field_missingness_by_quarter.csv"] = write_csv(
        report_dir / "field_missingness_by_quarter.csv",
        missingness_rows,
        ("Quarter", "Field", "Row count", "Non-null count", "Non-null percentage", "Zero percentage", "Validation status"),
    )
    report_hashes["field_distribution_by_quarter.csv"] = write_csv(
        report_dir / "field_distribution_by_quarter.csv",
        distribution_rows,
        ("Quarter", "Field", "Minimum", "Maximum", "Median", "Non-null percentage", "Zero percentage"),
    )
    report_hashes["institution_counts_by_quarter.csv"] = write_csv(
        report_dir / "institution_counts_by_quarter.csv",
        institution_rows,
        ("Quarter", "Institution count", "Quarter-over-quarter change", "Quarter-over-quarter percentage", "Validation status"),
    )
    report_hashes["schema_drift_events.csv"] = write_csv(
        report_dir / "schema_drift_events.csv",
        drift_rows,
        ("Quarter", "Field", "Expected schema", "Observed schema", "Severity", "Evidence", "Resolution status", "Recommended action"),
    )
    report_hashes["extraction_exceptions.csv"] = write_csv(
        report_dir / "extraction_exceptions.csv",
        exception_rows,
        ("Quarter", "Category", "Field", "Severity", "Evidence", "Status", "Action"),
    )
    return report_hashes


def freeze_required_report_views(report_hashes: dict[str, str]) -> None:
    run_report_dir: Path = ROOT / "reports" / "full_historical_extraction"
    for name, expected_hash in report_hashes.items():
        source: Path = run_report_dir / name
        if not source.exists():
            raise FullExtractionError(f"Run-scoped report is missing: {source}")
        observed_hash: str = sha256_file(source)
        if observed_hash != expected_hash:
            raise FullExtractionError(
                f"Run-scoped report hash mismatch: path={source}, "
                f"expected={expected_hash}, observed={observed_hash}"
            )
        write_once(ROOT / "reports" / name, source.read_bytes())


def run() -> None:
    log_dir: Path = ROOT / "logs" / "full_historical_extraction"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "extraction.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    config_path: Path = ROOT / "configs" / "full_historical_extraction.yaml"
    config: JsonObject = load_object(config_path)
    stored_hash: str = require_string(config, "configuration_hash")
    unhashed_config: JsonObject = {key: value for key, value in config.items() if key != "configuration_hash"}
    observed_hash: str = configuration_hash(unhashed_config)
    if stored_hash != observed_hash:
        raise FullExtractionError(
            f"Frozen configuration hash mismatch: stored={stored_hash}, observed={observed_hash}"
        )
    contract: JsonObject = load_object(ROOT / "configs" / "selected_financial_fields_v1.yaml")
    core_fields: tuple[str, ...] = validate_core_contract(contract)
    configured_fields: tuple[str, ...] = tuple(require_string_list(config, "requested_fields"))
    if configured_fields != core_fields:
        raise FullExtractionError("Frozen requested fields differ from approved ordered core contract")
    numeric_fields: frozenset[str] = numeric_fields_from_contract(contract, core_fields)
    quarters: tuple[Quarter, ...] = generate_quarters(
        require_string(config, "start_quarter"), require_string(config, "end_quarter")
    )
    if len(quarters) != require_int(config, "quarter_count"):
        raise FullExtractionError("Generated quarter count differs from frozen configuration")
    client, required, allowed = build_client(config)
    summaries: list[JsonObject] = []
    run_manifest_path: Path = ROOT / "manifests" / "full_historical_extraction" / "run_manifest.json"
    existing_success_manifest: JsonObject | None = None
    if run_manifest_path.exists():
        existing_manifest: JsonObject = load_object(run_manifest_path)
        if existing_manifest.get("status") == "PASS":
            existing_success_manifest = existing_manifest
    for position, quarter in enumerate(quarters, start=1):
        try:
            summary: JsonObject = execute_quarter(
                quarter, config, client, required, allowed, core_fields, numeric_fields
            )
        except Exception as error:
            failure_manifest: JsonObject = {
                "run_id": require_string(config, "run_id"),
                "configuration_hash": stored_hash,
                "status": failure_status(error),
                "failed_quarter": quarter.label,
                "completed_quarters": [str(row["quarter"]) for row in summaries],
                "error_type": type(error).__name__,
                "error": str(error),
                "updated_at": utc_now_text(),
            }
            write_replaceable_json(run_manifest_path, failure_manifest)
            LOGGER.exception("full_extraction_stopped", extra={"quarter": quarter.label})
            raise
        summaries.append(summary)
        progress_manifest: JsonObject = {
            "run_id": require_string(config, "run_id"),
            "configuration_hash": stored_hash,
            "status": "RUNNING",
            "expected_quarters": len(quarters),
            "completed_quarters": position,
            "last_completed_quarter": quarter.label,
            "total_rows_so_far": sum(int(row["row_count"]) for row in summaries),
            "total_pages_so_far": sum(int(row["page_count"]) for row in summaries),
            "updated_at": utc_now_text(),
        }
        write_replaceable_json(run_manifest_path, progress_manifest)
        print(
            f"progress={position}/{len(quarters)} quarter={quarter.label} "
            f"rows={summary['row_count']} status={summary['validation_status']}",
            flush=True,
        )
    report_hashes: dict[str, str] = build_reports(quarters, summaries, core_fields)
    quarter_paths: tuple[Path, ...] = tuple(
        ROOT / "data" / "interim" / "financials_by_quarter" / f"{quarter.label}.normalized.csv"
        for quarter in quarters
    )
    combined_path: Path = (
        ROOT
        / "data"
        / "processed"
        / "ingestion_stage"
        / "fdic_financials_2001q1_2026q1.parquet"
    )
    columns: tuple[str, ...] = (*core_fields, *LINEAGE_FIELDS)
    combined_rows, combined_hash = write_combined_parquet(
        quarter_paths, columns, combined_path
    )
    approved_rows: int = sum(int(row["row_count"]) for row in summaries)
    if combined_rows != approved_rows:
        raise FullExtractionError(
            f"Combined row count {combined_rows} differs from quarter total {approved_rows}"
        )
    report_dir: Path = ROOT / "reports" / "full_historical_extraction"
    reconciliation_hash: str = write_csv(
        report_dir / "combined_panel_reconciliation.csv",
        [
            {
                "Expected quarter count": len(quarters),
                "Observed quarter count": len(summaries),
                "Approved quarter row total": approved_rows,
                "Combined panel row count": combined_rows,
                "Difference": combined_rows - approved_rows,
                "Unique bank-quarter key": "PASS",
                "Combined panel SHA-256": combined_hash,
                "Validation result": "PASS",
            }
        ],
        ("Expected quarter count", "Observed quarter count", "Approved quarter row total", "Combined panel row count", "Difference", "Unique bank-quarter key", "Combined panel SHA-256", "Validation result"),
    )
    report_hashes["combined_panel_reconciliation.csv"] = reconciliation_hash
    freeze_required_report_views(report_hashes)
    finished_at: str = utc_now_text()
    original_completion: object = (
        None if existing_success_manifest is None else existing_success_manifest.get("completion_timestamp")
    )
    manifest_completion_timestamp: str = (
        str(original_completion) if isinstance(original_completion, str) else finished_at
    )
    parquet_created_timestamp: str = (
        datetime.fromtimestamp(combined_path.stat().st_mtime, timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    completion_timestamp: str = min(manifest_completion_timestamp, parquet_created_timestamp)
    retry_pages, retry_quarters = retry_summary(quarters)
    idempotent_rerun: bool = all(bool(row["skipped_as_complete"]) for row in summaries)
    stable_results: list[JsonObject] = [
        {key: value for key, value in row.items() if key != "skipped_as_complete"}
        for row in summaries
    ]
    final_manifest: JsonObject = {
        "run_id": require_string(config, "run_id"),
        "configuration_hash": stored_hash,
        "status": "PASS",
        "start_timestamp": require_string(config, "start_timestamp"),
        "completion_timestamp": completion_timestamp,
        "last_validation_timestamp": finished_at,
        "expected_quarters": len(quarters),
        "completed_quarters": len(summaries),
        "first_quarter": quarters[0].label,
        "last_quarter": quarters[-1].label,
        "total_rows": combined_rows,
        "total_pages": sum(int(row["page_count"]) for row in summaries),
        "pass_quarters": sum(1 for row in summaries if row["validation_status"] == "PASS"),
        "warning_quarters": sum(1 for row in summaries if row["validation_status"] == "PASS_WITH_WARNINGS"),
        "failed_quarters": 0,
        "retried_pages": retry_pages,
        "retried_quarters": list(retry_quarters),
        "combined_panel_path": str(combined_path.relative_to(ROOT)).replace("\\", "/"),
        "combined_panel_sha256": combined_hash,
        "report_hashes": report_hashes,
        "quarter_results": stable_results,
        "idempotency_check": {
            "status": "PASS" if idempotent_rerun else "NOT_A_RERUN",
            "checked_at": finished_at,
            "completed_quarters_skipped": len(summaries) if idempotent_rerun else 0,
            "combined_panel_hash_unchanged": (
                existing_success_manifest is not None
                and existing_success_manifest.get("combined_panel_sha256") == combined_hash
            ),
        },
    }
    write_replaceable_json(run_manifest_path, final_manifest)
    print(
        f"complete quarters={len(quarters)} rows={combined_rows} "
        f"pages={final_manifest['total_pages']} parquet_sha256={combined_hash}",
        flush=True,
    )


if __name__ == "__main__":
    run()
