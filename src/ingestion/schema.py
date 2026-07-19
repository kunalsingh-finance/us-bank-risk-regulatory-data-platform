"""Strict validation for FDIC BankFind Suite financial responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


Scalar: TypeAlias = str | int | float | bool | None
Record: TypeAlias = dict[str, Scalar]


class ResponseSchemaError(ValueError):
    """Raised when an FDIC response violates the expected schema."""


@dataclass(frozen=True)
class ValidatedPage:
    total: int
    records: list[Record]
    returned_fields: frozenset[str]
    index_name: str
    index_created_at: str


def require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ResponseSchemaError(f"Expected object for {context}; received {type(value).__name__}")
    return {str(key): item for key, item in value.items()}


def require_list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise ResponseSchemaError(f"Expected array for {context}; received {type(value).__name__}")
    return value


def require_int(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResponseSchemaError(f"Expected integer for {context}; received {value!r}")
    return value


def require_string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise ResponseSchemaError(f"Expected string for {context}; received {value!r}")
    return value


def validate_scalar(value: object, field: str) -> Scalar:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ResponseSchemaError(
        f"Field {field} contains unsupported value type {type(value).__name__}: {value!r}"
    )


def validate_response(
    payload: object,
    required_fields: frozenset[str],
    requested_fields: frozenset[str],
    allowed_unexpected_fields: frozenset[str],
) -> ValidatedPage:
    root: dict[str, object] = require_mapping(payload, "response")
    meta: dict[str, object] = require_mapping(root.get("meta"), "meta")
    total: int = require_int(meta.get("total"), "meta.total")
    if total < 0:
        raise ResponseSchemaError(f"meta.total must be non-negative; received {total}")
    index: dict[str, object] = require_mapping(meta.get("index"), "meta.index")
    index_name: str = require_string(index.get("name"), "meta.index.name")
    index_created_at: str = require_string(
        index.get("createTimestamp"), "meta.index.createTimestamp"
    )
    wrappers: list[object] = require_list(root.get("data"), "data")
    records: list[Record] = []
    returned_fields: set[str] = set()
    for position, wrapper_value in enumerate(wrappers):
        wrapper: dict[str, object] = require_mapping(wrapper_value, f"data[{position}]")
        raw_record: dict[str, object] = require_mapping(
            wrapper.get("data"), f"data[{position}].data"
        )
        record: Record = {
            field: validate_scalar(value, field) for field, value in raw_record.items()
        }
        missing_required: frozenset[str] = required_fields.difference(record)
        if missing_required:
            raise ResponseSchemaError(
                f"Record {position} is missing required fields: {sorted(missing_required)}"
            )
        returned_fields.update(record)
        records.append(record)
    unexpected: set[str] = returned_fields.difference(requested_fields).difference(
        allowed_unexpected_fields
    )
    if unexpected:
        raise ResponseSchemaError(f"Response returned unexpected fields: {sorted(unexpected)}")
    return ValidatedPage(
        total=total,
        records=records,
        returned_fields=frozenset(returned_fields),
        index_name=index_name,
        index_created_at=index_created_at,
    )


def validate_quarter_end(value: Scalar, expected_report_date: str) -> None:
    normalized: str = str(value) if value is not None else ""
    if normalized != expected_report_date:
        raise ResponseSchemaError(
            f"Expected REPDTE {expected_report_date}; received {normalized or '<missing>'}"
        )


def find_duplicate_bank_quarters(records: list[Record]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for record in records:
        cert: str = "" if record.get("CERT") is None else str(record["CERT"])
        report_date: str = "" if record.get("REPDTE") is None else str(record["REPDTE"])
        key: tuple[str, str] = (cert, report_date)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)

