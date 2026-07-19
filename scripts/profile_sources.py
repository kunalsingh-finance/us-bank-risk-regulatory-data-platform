"""Stream and profile immutable Phase 0 CSV and YAML sources."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


NULL_TOKENS: Final[frozenset[str]] = frozenset({"", "null", "none", "na", "n/a"})
DATE_FIELD_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:DATE|DTE|YEAR|YMD)$", re.IGNORECASE)
YAML_PROPERTY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\s{6}([A-Za-z0-9_]+):\s*$")


@dataclass(frozen=True)
class CsvProfile:
    path: str
    bytes: int
    sha256: str
    modified_at: str
    row_count: int
    column_count: int
    columns: list[str]
    missing_count: dict[str, int]
    duplicate_full_rows: int
    candidate_key_duplicates: dict[str, int]
    date_coverage: dict[str, dict[str, str | int | None]]


@dataclass(frozen=True)
class YamlProfile:
    path: str
    bytes: int
    sha256: str
    modified_at: str
    property_count: int
    properties: list[str]


def calculate_sha256(path: Path) -> str:
    digest: hashlib._Hash = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_value(value: str | None) -> str:
    return "" if value is None else value.strip()


def is_missing(value: str | None) -> bool:
    return normalized_value(value).lower() in NULL_TOKENS


def candidate_key_fields(columns: list[str]) -> list[str]:
    priorities: tuple[str, ...] = (
        "ID",
        "CERT",
        "RSSDID",
        "REPDTE",
        "RISDATE",
        "FAILDATE",
        "EFFDATE",
        "TRANSNUM",
        "Variable Name",
    )
    return [field for field in priorities if field in columns]


def initialize_coverage(columns: list[str]) -> dict[str, dict[str, str | int | None]]:
    return {
        field: {"min": None, "max": None, "non_missing": 0}
        for field in columns
        if DATE_FIELD_PATTERN.search(field)
    }


def update_coverage(coverage: dict[str, dict[str, str | int | None]], row: dict[str, str]) -> None:
    for field, summary in coverage.items():
        value: str = normalized_value(row.get(field))
        if is_missing(value):
            continue
        current_min: str | None = summary["min"] if isinstance(summary["min"], str) else None
        current_max: str | None = summary["max"] if isinstance(summary["max"], str) else None
        summary["min"] = value if current_min is None or value < current_min else current_min
        summary["max"] = value if current_max is None or value > current_max else current_max
        summary["non_missing"] = int(summary["non_missing"] or 0) + 1


def profile_csv(path: Path, root: Path) -> CsvProfile:
    missing: Counter[str] = Counter()
    full_rows: Counter[str] = Counter()
    key_counts: dict[str, Counter[str]] = {}
    row_count: int = 0
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        first_line: str = handle.readline()
        if "," in first_line:
            handle.seek(0)
        reader: csv.DictReader[str] = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        columns: list[str] = [field.strip() for field in reader.fieldnames]
        key_fields: list[str] = candidate_key_fields(columns)
        key_counts = {field: Counter() for field in key_fields}
        coverage: dict[str, dict[str, str | int | None]] = initialize_coverage(columns)
        for row in reader:
            row_count += 1
            values: list[str] = [normalized_value(row.get(field)) for field in columns]
            for field, value in zip(columns, values, strict=True):
                if is_missing(value):
                    missing[field] += 1
            for field in key_fields:
                value = normalized_value(row.get(field))
                if not is_missing(value):
                    key_counts[field][value] += 1
            update_coverage(coverage, row)
            row_fingerprint: str = hashlib.blake2b(
                "\x1f".join(values).encode("utf-8", errors="replace"), digest_size=16
            ).hexdigest()
            full_rows[row_fingerprint] += 1

    duplicates: dict[str, int] = {
        field: sum(count - 1 for count in counts.values() if count > 1)
        for field, counts in key_counts.items()
    }
    return CsvProfile(
        path=path.relative_to(root).as_posix(),
        bytes=path.stat().st_size,
        sha256=calculate_sha256(path),
        modified_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        missing_count={field: missing[field] for field in columns},
        duplicate_full_rows=sum(count - 1 for count in full_rows.values() if count > 1),
        candidate_key_duplicates=duplicates,
        date_coverage=coverage,
    )


def profile_yaml(path: Path, root: Path) -> YamlProfile:
    text: str = path.read_text(encoding="utf-8-sig", errors="strict")
    properties: list[str] = []
    in_data_properties: bool = False
    for line in text.splitlines():
        if line == "    properties:":
            in_data_properties = True
            continue
        if in_data_properties and line and not line.startswith("      "):
            in_data_properties = False
        if in_data_properties:
            match: re.Match[str] | None = YAML_PROPERTY_PATTERN.match(line)
            if match is not None:
                properties.append(match.group(1))
    return YamlProfile(
        path=path.relative_to(root).as_posix(),
        bytes=path.stat().st_size,
        sha256=calculate_sha256(path),
        modified_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        property_count=len(properties),
        properties=properties,
    )


def main() -> None:
    root: Path = Path(__file__).resolve().parents[1]
    raw: Path = root / "data" / "raw"
    csv_paths: list[Path] = sorted(raw.glob("*.csv"))
    yaml_paths: list[Path] = sorted((raw / "definitions").glob("*.yaml"))
    if len(csv_paths) != 6 or len(yaml_paths) != 4:
        raise FileNotFoundError(
            f"Expected 6 CSV and 4 YAML files; found {len(csv_paths)} CSV and {len(yaml_paths)} YAML"
        )
    result: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "csv_profiles": [asdict(profile_csv(path, root)) for path in csv_paths],
        "yaml_profiles": [asdict(profile_yaml(path, root)) for path in yaml_paths],
    }
    output: Path = root / "reports" / "phase0_source_profile.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
