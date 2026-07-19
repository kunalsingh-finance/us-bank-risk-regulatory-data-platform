"""Pure controls for deterministic full-history FDIC extraction."""

from __future__ import annotations

import csv
import io
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TypeAlias

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from .manifest import canonical_json_bytes, sha256_bytes, sha256_file, write_once
from .schema import Record, Scalar, find_duplicate_bank_quarters


JsonObject: TypeAlias = dict[str, object]
QUARTER_PATTERN: re.Pattern[str] = re.compile(r"^(?P<year>\d{4})_Q(?P<quarter>[1-4])$")
QUARTER_ENDS: dict[int, str] = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}
LINEAGE_FIELDS: tuple[str, ...] = (
    "ingestion_run_id",
    "source_endpoint",
    "requested_quarter",
    "source_page_count",
    "source_manifest_path",
    "extraction_timestamp",
    "downloader_version",
    "configuration_hash",
    "quarter_raw_hash",
    "normalization_version",
    "validation_status",
)
MISSING_TOKENS: frozenset[str] = frozenset({"", "null", "none", "na", "n/a"})


class QuarterConfigurationError(ValueError):
    """Raised when a requested quarter range or field contract is invalid."""


class NumericValueError(ValueError):
    """Raised when a nonmissing financial value is not a finite number."""


class QuarterValidationError(RuntimeError):
    """Raised when a quarter fails an ingestion quality control."""


@dataclass(frozen=True)
class Quarter:
    label: str
    report_date: str


@dataclass(frozen=True)
class QuarterValidation:
    status: str
    row_count: int
    unique_cert_count: int
    unique_rssdid_count: int
    duplicate_count: int
    missing_cert_count: int
    missing_rssdid_count: int
    missing_date_count: int
    invalid_numeric_count: int
    missing_fields: tuple[str, ...]
    all_null_fields: tuple[str, ...]


def parse_quarter(label: str) -> tuple[int, int]:
    match: re.Match[str] | None = QUARTER_PATTERN.fullmatch(label)
    if match is None:
        raise QuarterConfigurationError(
            f"Quarter must use YYYY_Q# with Q1-Q4; received {label!r}"
        )
    return int(match.group("year")), int(match.group("quarter"))


def quarter_from_index(index: int) -> Quarter:
    year: int = index // 4
    quarter_number: int = index % 4 + 1
    label: str = f"{year:04d}_Q{quarter_number}"
    return Quarter(label=label, report_date=f"{year:04d}{QUARTER_ENDS[quarter_number]}")


def generate_quarters(start_label: str, end_label: str) -> tuple[Quarter, ...]:
    start_year, start_quarter = parse_quarter(start_label)
    end_year, end_quarter = parse_quarter(end_label)
    start_index: int = start_year * 4 + start_quarter - 1
    end_index: int = end_year * 4 + end_quarter - 1
    if start_index > end_index:
        raise QuarterConfigurationError(
            f"Start quarter {start_label} is after end quarter {end_label}"
        )
    return tuple(quarter_from_index(index) for index in range(start_index, end_index + 1))


def configuration_hash(config_without_hash: JsonObject) -> str:
    if "configuration_hash" in config_without_hash:
        raise QuarterConfigurationError(
            "configuration_hash must be excluded when calculating the configuration digest"
        )
    return sha256_bytes(canonical_json_bytes(config_without_hash))


def is_missing(value: Scalar | str | None) -> bool:
    return value is None or str(value).strip().lower() in MISSING_TOKENS


def scalar_text(value: Scalar | str | None) -> str:
    return "" if value is None else str(value)


def validate_numeric_value(value: Scalar | str | None, field: str) -> None:
    if is_missing(value):
        return
    if isinstance(value, bool):
        raise NumericValueError(f"Numeric field {field} contains boolean value {value!r}")
    try:
        number: Decimal = Decimal(str(value))
    except InvalidOperation as error:
        raise NumericValueError(
            f"Numeric field {field} contains invalid value {value!r}"
        ) from error
    if not number.is_finite():
        raise NumericValueError(
            f"Numeric field {field} contains non-finite value {value!r}"
        )


def numeric_fields_from_contract(contract: JsonObject, core_fields: tuple[str, ...]) -> frozenset[str]:
    raw_fields: object = contract.get("fields")
    if not isinstance(raw_fields, list):
        raise QuarterConfigurationError("Field contract fields must be an array")
    types: dict[str, str] = {}
    for raw_entry in raw_fields:
        if not isinstance(raw_entry, dict):
            raise QuarterConfigurationError("Field contract entries must be objects")
        code: object = raw_entry.get("api_field_code")
        expected_type: object = raw_entry.get("expected_data_type")
        classification: object = raw_entry.get("final_classification")
        if isinstance(code, str) and isinstance(expected_type, str) and classification == "Core":
            types[code] = expected_type
    missing: list[str] = sorted(set(core_fields).difference(types))
    if missing:
        raise QuarterConfigurationError(
            f"Core query fields are missing Core contract entries: {missing}"
        )
    return frozenset(
        field for field in core_fields if types[field].lower() in {"number", "integer", "float"}
    )


def validate_core_contract(contract: JsonObject) -> tuple[str, ...]:
    raw_core: object = contract.get("approved_core_query")
    raw_fields: object = contract.get("fields")
    if not isinstance(raw_core, list) or not all(isinstance(value, str) for value in raw_core):
        raise QuarterConfigurationError("approved_core_query must be a string array")
    if not isinstance(raw_fields, list):
        raise QuarterConfigurationError("fields must be an array")
    core_fields: tuple[str, ...] = tuple(str(value) for value in raw_core)
    if len(core_fields) != 40 or len(set(core_fields)) != 40:
        raise QuarterConfigurationError(
            f"Approved core query must contain exactly 40 unique fields; found {len(core_fields)}"
        )
    classification: dict[str, object] = {
        str(entry.get("api_field_code")): entry.get("final_classification")
        for entry in raw_fields
        if isinstance(entry, dict)
    }
    leaks: list[str] = [field for field in core_fields if classification.get(field) != "Core"]
    if leaks:
        raise QuarterConfigurationError(
            f"Approved query includes non-Core or undocumented fields: {leaks}"
        )
    prohibited: set[str] = {
        code for code, value in classification.items() if value in {"Conditional", "Replace", "Derived", "Remove", "Unresolved"}
    }
    overlap: list[str] = sorted(set(core_fields).intersection(prohibited))
    if overlap:
        raise QuarterConfigurationError(f"Non-Core field leakage detected: {overlap}")
    return core_fields


def validate_records(
    records: list[Record],
    quarter: Quarter,
    core_fields: tuple[str, ...],
    numeric_fields: frozenset[str],
) -> QuarterValidation:
    if not records:
        raise QuarterValidationError(f"Quarter {quarter.label} returned zero rows")
    returned_fields: set[str] = set().union(*(record.keys() for record in records))
    missing_fields: tuple[str, ...] = tuple(sorted(set(core_fields).difference(returned_fields)))
    if missing_fields:
        raise QuarterValidationError(
            f"Quarter {quarter.label} is missing core fields: {list(missing_fields)}"
        )
    all_null_fields: tuple[str, ...] = tuple(
        field for field in core_fields if all(is_missing(record.get(field)) for record in records)
    )
    if all_null_fields:
        raise QuarterValidationError(
            f"Quarter {quarter.label} has entirely null core fields: {list(all_null_fields)}"
        )
    missing_cert_count: int = 0
    missing_rssdid_count: int = 0
    missing_date_count: int = 0
    invalid_numeric_count: int = 0
    for position, record in enumerate(records):
        cert: str = scalar_text(record.get("CERT")).strip()
        if not cert:
            missing_cert_count += 1
        elif not cert.isdigit():
            raise QuarterValidationError(
                f"Quarter {quarter.label} record {position} has non-parseable CERT {cert!r}"
            )
        if is_missing(record.get("RSSDID")):
            missing_rssdid_count += 1
        report_date: str = scalar_text(record.get("REPDTE"))
        if not report_date:
            missing_date_count += 1
        elif report_date != quarter.report_date:
            raise QuarterValidationError(
                f"Quarter {quarter.label} record {position} has REPDTE {report_date!r}; "
                f"expected {quarter.report_date}"
            )
        for field in numeric_fields:
            try:
                validate_numeric_value(record.get(field), field)
            except NumericValueError as error:
                invalid_numeric_count += 1
                raise QuarterValidationError(
                    f"Quarter {quarter.label} record {position}: {error}"
                ) from error
    duplicates: list[tuple[str, str]] = find_duplicate_bank_quarters(records)
    if duplicates:
        raise QuarterValidationError(
            f"Quarter {quarter.label} has duplicate CERT-report-date keys: {duplicates[:10]}"
        )
    if missing_cert_count > 0 or missing_date_count > 0:
        raise QuarterValidationError(
            f"Quarter {quarter.label} has missing identifiers: CERT={missing_cert_count}, "
            f"REPDTE={missing_date_count}"
        )
    status: str = "PASS_WITH_WARNINGS" if missing_rssdid_count > 0 else "PASS"
    return QuarterValidation(
        status=status,
        row_count=len(records),
        unique_cert_count=len({scalar_text(record.get("CERT")) for record in records}),
        unique_rssdid_count=len(
            {scalar_text(record.get("RSSDID")) for record in records if not is_missing(record.get("RSSDID"))}
        ),
        duplicate_count=0,
        missing_cert_count=missing_cert_count,
        missing_rssdid_count=missing_rssdid_count,
        missing_date_count=missing_date_count,
        invalid_numeric_count=invalid_numeric_count,
        missing_fields=missing_fields,
        all_null_fields=all_null_fields,
    )


def numeric_statistics(values: list[Scalar]) -> JsonObject:
    present: list[Scalar] = [value for value in values if not is_missing(value)]
    decimals: list[Decimal] = []
    for value in present:
        validate_numeric_value(value, "statistics")
        decimals.append(Decimal(str(value)))
    total: int = len(values)
    zero_count: int = sum(1 for value in decimals if value == 0)
    sorted_values: list[Decimal] = sorted(decimals)
    median: Decimal | None = None
    if sorted_values:
        midpoint: int = len(sorted_values) // 2
        median = (
            sorted_values[midpoint]
            if len(sorted_values) % 2 == 1
            else (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2
        )
    return {
        "row_count": total,
        "non_null_count": len(present),
        "non_null_percentage": 0.0 if total == 0 else 100.0 * len(present) / total,
        "zero_percentage": 0.0 if total == 0 else 100.0 * zero_count / total,
        "minimum": None if not decimals else str(min(decimals)),
        "maximum": None if not decimals else str(max(decimals)),
        "median": None if median is None else str(median),
    }


def text_statistics(values: list[Scalar]) -> JsonObject:
    present: list[str] = [scalar_text(value) for value in values if not is_missing(value)]
    total: int = len(values)
    return {
        "row_count": total,
        "non_null_count": len(present),
        "non_null_percentage": 0.0 if total == 0 else 100.0 * len(present) / total,
        "zero_percentage": 0.0,
        "minimum": None if not present else min(present),
        "maximum": None if not present else max(present),
        "median": None,
    }


def field_statistics(
    records: list[Record], core_fields: tuple[str, ...], numeric_fields: frozenset[str]
) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for field in core_fields:
        values: list[Scalar] = [record.get(field) for record in records]
        stats: JsonObject = (
            numeric_statistics(values) if field in numeric_fields else text_statistics(values)
        )
        rows.append({"field": field, **stats})
    return rows


def sorted_records(records: list[Record]) -> list[Record]:
    return sorted(
        records,
        key=lambda record: (
            int(scalar_text(record.get("CERT"))),
            scalar_text(record.get("REPDTE")),
        ),
    )


def source_csv_bytes(records: list[Record], core_fields: tuple[str, ...]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(core_fields), lineterminator="\n")
    writer.writeheader()
    for record in sorted_records(records):
        writer.writerow({field: scalar_text(record.get(field)) for field in core_fields})
    return output.getvalue().encode("utf-8")


def lineage_csv_bytes(
    records: list[Record],
    core_fields: tuple[str, ...],
    lineage: dict[str, str],
) -> bytes:
    expected_lineage: set[str] = set(LINEAGE_FIELDS)
    if set(lineage) != expected_lineage:
        raise QuarterConfigurationError(
            f"Lineage fields do not match contract: expected={sorted(expected_lineage)}, "
            f"observed={sorted(lineage)}"
        )
    columns: list[str] = [*core_fields, *LINEAGE_FIELDS]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for record in sorted_records(records):
        row: dict[str, str] = {field: scalar_text(record.get(field)) for field in core_fields}
        row.update(lineage)
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def raw_jsonl_bytes(records: list[Record], core_fields: tuple[str, ...]) -> bytes:
    lines: list[bytes] = []
    for record in sorted_records(records):
        source_record: dict[str, Scalar] = {field: record.get(field) for field in core_fields}
        lines.append(canonical_json_bytes(source_record))
    return b"\n".join(lines) + b"\n"


def verify_page_manifests(output_dir: Path) -> tuple[int, int]:
    manifests: list[Path] = sorted(output_dir.glob("page_*.manifest.json"))
    if not manifests:
        raise QuarterValidationError(f"No page manifests found in {output_dir}")
    row_total: int = 0
    offsets: list[int] = []
    for manifest_path in manifests:
        payload: object = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise QuarterValidationError(f"Page manifest is not an object: {manifest_path}")
        offset: object = payload.get("offset")
        row_count: object = payload.get("row_count")
        expected_hash: object = payload.get("response_sha256")
        if not isinstance(offset, int) or not isinstance(row_count, int) or not isinstance(expected_hash, str):
            raise QuarterValidationError(f"Page manifest is incomplete: {manifest_path}")
        raw_path: Path = manifest_path.with_name(manifest_path.name.replace(".manifest.json", ".json"))
        if not raw_path.exists():
            raise QuarterValidationError(f"Raw page is missing for manifest {manifest_path}")
        observed_hash: str = sha256_file(raw_path)
        if observed_hash != expected_hash:
            raise QuarterValidationError(
                f"Raw page hash mismatch: path={raw_path}, expected={expected_hash}, observed={observed_hash}"
            )
        offsets.append(offset)
        row_total += row_count
    if offsets != sorted(set(offsets)):
        raise QuarterValidationError(f"Duplicate or unordered page offsets in {output_dir}: {offsets}")
    return len(manifests), row_total


def completion_marker_is_valid(path: Path, configuration_digest: str) -> bool:
    if not path.exists():
        return False
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise QuarterValidationError(f"Completion marker is not an object: {path}")
    return (
        payload.get("configuration_hash") == configuration_digest
        and payload.get("validation_status") in {"PASS", "PASS_WITH_WARNINGS"}
    )


def write_combined_parquet(
    quarter_csv_paths: tuple[Path, ...],
    columns: tuple[str, ...],
    output_path: Path,
) -> tuple[int, str]:
    if not quarter_csv_paths:
        raise QuarterValidationError("No normalized quarter files were supplied for combination")
    column_types: dict[str, pa.DataType] = {column: pa.string() for column in columns}
    tables: list[pa.Table] = []
    for path in quarter_csv_paths:
        if not path.exists():
            raise QuarterValidationError(f"Normalized quarter file is missing: {path}")
        table: pa.Table = pacsv.read_csv(
            path,
            convert_options=pacsv.ConvertOptions(column_types=column_types),
        )
        if tuple(table.column_names) != columns:
            raise QuarterValidationError(
                f"Normalized schema mismatch: path={path}, expected={columns}, observed={tuple(table.column_names)}"
            )
        tables.append(table)
    combined: pa.Table = pa.concat_tables(tables)
    certs: list[str | None] = combined.column("CERT").to_pylist()
    dates: list[str | None] = combined.column("REPDTE").to_pylist()
    keys: list[tuple[str | None, str | None]] = list(zip(certs, dates, strict=True))
    if len(keys) != len(set(keys)):
        raise QuarterValidationError("Combined panel contains duplicate CERT-REPDTE keys")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path = output_path.with_name(f".{output_path.name}.tmp")
    pq.write_table(combined, temporary, compression="zstd", use_dictionary=True)
    content: bytes = temporary.read_bytes()
    temporary.unlink()
    digest: str = write_once(output_path, content)
    return combined.num_rows, digest


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def finite_float(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QuarterConfigurationError(f"Expected numeric {context}; received {value!r}")
    result: float = float(value)
    if not math.isfinite(result):
        raise QuarterConfigurationError(f"Expected finite numeric {context}; received {value!r}")
    return result
