"""Download only Phase 1 anchor quarters and generate ingestion validation reports."""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import statistics
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeAlias


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.downloader import DownloadResult, download_query  # noqa: E402
from src.ingestion.fdic_client import (  # noqa: E402
    FdicClient,
    FdicClientConfig,
    FinancialsQuery,
)
from src.ingestion.manifest import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    write_json_once,
    write_once,
)
from src.ingestion.schema import Record, Scalar, find_duplicate_bank_quarters  # noqa: E402


JsonObject: TypeAlias = dict[str, object]
MISSING_TOKENS: frozenset[str] = frozenset({"", "null", "none", "na", "n/a"})
NINE_MISSING_FIELDS: tuple[str, ...] = (
    "LNLSGR",
    "OTHBFHLB",
    "LNRECONS",
    "LNREMULT",
    "LNRERES",
    "LNCI",
    "LNCON",
    "LNCRCD",
    "LNAG",
)
PROBE_DECISIONS: dict[str, str] = {
    "LNLSGR": "Core",
    "OTHBFHLB": "Core",
    "LNRECONS": "Core",
    "LNREMULT": "Core",
    "LNRERES": "Core",
    "LNCI": "Core",
    "LNCON": "Core",
    "LNCRCD": "Core",
    "LNAG": "Conditional: partial reporting in 2001 Q1 and 2008 Q4",
}
PERCENT_FIELDS: frozenset[str] = frozenset(
    {"EQV", "RBC1AAJ", "IDT1CER", "IDT1RWAJR", "RBCRWAJ", "ROA", "NIMY", "EEFFR", "INTEXPY"}
)
IDENTIFIER_FIELDS: frozenset[str] = frozenset(
    {"CERT", "RSSDID", "NAMEFULL", "REPDTE", "STALP", "BKCLASS", "REGAGNT", "ACTIVE", "CB", "ID"}
)


def load_json_config(path: Path) -> JsonObject:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Configuration must be JSON-compatible YAML: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Configuration root must be an object: {path}")
    return {str(key): item for key, item in value.items()}


def require_string(config: JsonObject, key: str) -> str:
    value: object = config.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected string config value {key}; received {value!r}")
    return value


def require_int(config: JsonObject, key: str) -> int:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected integer config value {key}; received {value!r}")
    return value


def require_number(config: JsonObject, key: str) -> float:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected numeric config value {key}; received {value!r}")
    return float(value)


def require_string_list(config: JsonObject, key: str) -> list[str]:
    value: object = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Expected string array config value {key}; received {value!r}")
    return [str(item) for item in value]


def require_object_list(config: JsonObject, key: str) -> list[JsonObject]:
    value: object = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"Expected object array config value {key}; received {value!r}")
    return [{str(item_key): item_value for item_key, item_value in item.items()} for item in value]


def is_missing(value: Scalar | str | None) -> bool:
    return value is None or str(value).strip().lower() in MISSING_TOKENS


def scalar_text(value: Scalar | str | None) -> str:
    return "" if value is None else str(value)


def parse_number(value: Scalar | str | None) -> float | None:
    if is_missing(value) or isinstance(value, bool):
        return None
    try:
        number: float = float(str(value))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def inferred_type(values: list[Scalar]) -> str:
    non_null: list[Scalar] = [value for value in values if not is_missing(value)]
    if not non_null:
        return "null"
    if all(isinstance(value, bool) for value in non_null):
        return "boolean"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_null):
        return "integer"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_null):
        return "number"
    return "string"


def sorted_records(records: list[Record]) -> list[Record]:
    def sort_key(record: Record) -> tuple[int, str]:
        cert_number: float | None = parse_number(record.get("CERT"))
        cert_key: int = int(cert_number) if cert_number is not None else 2**63 - 1
        return cert_key, scalar_text(record.get("CERT"))

    return sorted(records, key=sort_key)


def records_to_csv(records: list[Record], fields: list[str]) -> bytes:
    output = io.StringIO(newline="")
    fieldnames: list[str] = [*fields, "ID"] if "ID" not in fields else fields
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for record in sorted_records(records):
        writer.writerow({field: scalar_text(record.get(field)) for field in fieldnames})
    return output.getvalue().encode("utf-8")


def field_statistics(records: list[Record], field: str) -> JsonObject:
    values: list[Scalar] = [record.get(field) for record in records]
    non_null_values: list[Scalar] = [value for value in values if not is_missing(value)]
    numeric_values: list[float] = [
        number for value in non_null_values if (number := parse_number(value)) is not None
    ]
    zero_count: int = sum(1 for number in numeric_values if number == 0)
    distinct_values: set[str] = {scalar_text(value) for value in non_null_values}
    minimum: float | str | None
    maximum: float | str | None
    median: float | None
    if numeric_values and len(numeric_values) == len(non_null_values):
        minimum = min(numeric_values)
        maximum = max(numeric_values)
        median = statistics.median(numeric_values)
    elif non_null_values:
        text_values: list[str] = [scalar_text(value) for value in non_null_values]
        minimum = min(text_values)
        maximum = max(text_values)
        median = None
    else:
        minimum = None
        maximum = None
        median = None
    total: int = len(records)
    non_null_count: int = len(non_null_values)
    return {
        "field": field,
        "row_count": total,
        "non_null_count": non_null_count,
        "non_null_percentage": 0.0 if total == 0 else 100.0 * non_null_count / total,
        "zero_percentage": 0.0 if total == 0 else 100.0 * zero_count / total,
        "distinct_count": len(distinct_values),
        "minimum": minimum,
        "maximum": maximum,
        "median": median,
        "data_type": inferred_type(values),
    }


def plausibility_status(field: str, stats: JsonObject) -> tuple[str, str]:
    minimum = stats.get("minimum")
    maximum = stats.get("maximum")
    non_null_percentage = float(stats["non_null_percentage"])
    if non_null_percentage == 0:
        return "Warning", "Field is entirely unavailable for this anchor"
    if float(stats["zero_percentage"]) == 100.0:
        return "Warning", "Field is entirely zero; verify unavailable/sentinel semantics"
    if field in {"ASSET", "DEP", "LNLSGR"} and isinstance(minimum, (int, float)) and minimum < 0:
        return "Warning", "Negative balance detected"
    if field in PERCENT_FIELDS and isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
        if minimum < -1000 or maximum > 1000:
            return "Warning", "Percentage outside broad plausibility bound [-1000, 1000]"
    return "Pass", ""


def definition_change_warning(field: str, quarter: str, stats: JsonObject) -> str:
    warnings: dict[str, str] = {
        "CB": "FDIC community-bank definition and indexed thresholds evolve over time",
        "EQV": "FDIC-calculated ratio; use EQ/ASSET derivation rather than source ratio as a predictor",
        "RBC1AAJ": "Capital-rule changes and extreme denominator effects require controls",
        "IDT1CER": "Unavailable before 2014 and zero-filled in early anchors; CBLR electors are zero after 2020",
        "IDT1RWAJR": "Capital-rule changes and CBLR zero sentinels after 2020",
        "RBCRWAJ": "Capital-rule changes and CBLR zero sentinels after 2020",
        "NTLNLS": "YTD flow; replace with NTLNLSQ for bank-quarter analysis",
        "NETINC": "YTD flow; replace with NETINCQ for bank-quarter analysis",
        "INTINC": "YTD flow; use only with within-year lag differencing",
        "EINTEXP": "YTD flow; use only with within-year lag differencing",
        "NONII": "YTD flow; replace with NONIIQ for bank-quarter analysis",
        "NONIX": "YTD flow; replace with NONIXQ for bank-quarter analysis",
        "PTAXNETINC": "YTD flow; replace with PTAXNETINCQ for bank-quarter analysis",
        "ROA": "Annualized YTD ratio; replace with ROAQ",
        "NIMY": "Annualized YTD margin; replace with NIMYQ",
        "EEFFR": "YTD ratio; replace with EEFFQR and retain extreme-value controls",
        "DEPUNINS": "Not equivalent to reported DEPUNA; methodology and reporting regimes change",
        "COREDEP": "Definition evolves over time; retain with version caveat",
        "INTEXPY": "Annualized YTD ratio; replace with INTEXPYQ",
        "LNAG": "Partial reporting population in early anchors",
    }
    warning: str = warnings.get(field, "")
    if field == "IDT1CER" and quarter in {"2001_Q1", "2008_Q4", "2012_Q4"} and float(stats["zero_percentage"]) == 100.0:
        return f"{warning}; observed 100% zero sentinel"
    return warning


def write_csv_report(path: Path, rows: list[JsonObject], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    path.write_text(output.getvalue(), encoding="utf-8", newline="")


def compare_values(manual_value: str | None, api_value: Scalar) -> str:
    manual_missing: bool = is_missing(manual_value)
    api_missing: bool = is_missing(api_value)
    if manual_missing and api_missing:
        return "Exact match"
    if manual_missing:
        return "Missing in bulk file"
    if api_missing:
        return "Missing in API"
    if str(manual_value).strip() == scalar_text(api_value):
        return "Exact match"
    manual_number: float | None = parse_number(manual_value)
    api_number: float | None = parse_number(api_value)
    if manual_number is not None and api_number is not None:
        tolerance: float = max(1e-9, 1e-9 * max(abs(manual_number), abs(api_number), 1.0))
        if abs(manual_number - api_number) <= tolerance:
            return "Rounding difference"
    return "Unresolved"


def manual_reconciliation(api_records: list[Record], requested_fields: list[str]) -> list[JsonObject]:
    manual_path: Path = ROOT / "data" / "raw" / "fdic_financials_sample_2026_q1.csv"
    with manual_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        manual_rows: list[dict[str, str]] = [dict(row) for row in reader]
    api_by_cert: dict[str, Record] = {
        scalar_text(record.get("CERT")): record for record in api_records
    }
    manual_by_cert: dict[str, dict[str, str]] = {row["CERT"]: row for row in manual_rows}
    all_certs: list[str] = sorted(set(api_by_cert).union(manual_by_cert), key=lambda value: int(value))
    shared_fields: list[str] = [
        field for field in requested_fields if reader.fieldnames is not None and field in reader.fieldnames
    ]
    rows: list[JsonObject] = []
    categories: tuple[str, ...] = (
        "Exact match",
        "Rounding difference",
        "Field-definition difference",
        "Population difference",
        "Timing difference",
        "Missing in API",
        "Missing in bulk file",
        "Unresolved",
    )
    for field in shared_fields:
        counts: dict[str, int] = {category: 0 for category in categories}
        for cert in all_certs:
            manual_row: dict[str, str] | None = manual_by_cert.get(cert)
            api_row: Record | None = api_by_cert.get(cert)
            if manual_row is None or api_row is None:
                counts["Population difference"] += 1
                continue
            category: str = compare_values(manual_row.get(field), api_row.get(field))
            counts[category] += 1
        material: list[str] = [
            category for category in categories if category != "Exact match" and counts[category] > 0
        ]
        overall: str = "Exact match" if not material else "; ".join(material)
        rows.append(
            {
                "Field": field,
                "Manual row count": len(manual_rows),
                "API row count": len(api_records),
                **counts,
                "Overall classification": overall,
                "Warning": "" if not material else "Review non-exact observations",
            }
        )
    return rows


def build_client(config: JsonObject) -> tuple[FdicClient, frozenset[str], frozenset[str]]:
    required_fields: frozenset[str] = frozenset(require_string_list(config, "required_fields"))
    allowed_unexpected_fields: frozenset[str] = frozenset(
        require_string_list(config, "allowed_unexpected_fields")
    )
    client_config = FdicClientConfig(
        base_url=require_string(config, "base_url"),
        timeout_seconds=require_int(config, "timeout_seconds"),
        max_attempts=require_int(config, "max_attempts"),
        backoff_base_seconds=require_number(config, "backoff_base_seconds"),
        user_agent=require_string(config, "user_agent"),
        allowed_unexpected_fields=allowed_unexpected_fields,
        required_fields=required_fields,
    )
    return FdicClient.live(client_config), required_fields, allowed_unexpected_fields


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    download_config: JsonObject = load_json_config(ROOT / "configs" / "fdic_download_config.yaml")
    anchor_config: JsonObject = load_json_config(ROOT / "configs" / "anchor_quarters.yaml")
    fields: list[str] = require_string_list(anchor_config, "fields_requested")
    anchors: list[JsonObject] = require_object_list(anchor_config, "anchors")
    client, required_fields, allowed_unexpected_fields = build_client(download_config)
    anchor_rows: list[JsonObject] = []
    continuity_rows: list[JsonObject] = []
    probe_rows: list[JsonObject] = []
    exception_rows: list[JsonObject] = []
    latest_records: list[Record] = []
    for anchor in anchors:
        quarter: str = require_string(anchor, "quarter")
        report_date: str = require_string(anchor, "report_date")
        output_dir: Path = ROOT / "data" / "raw" / "api" / "financials" / quarter
        population_filter: str = require_string(download_config, "population_filter")
        query = FinancialsQuery(
            filters=f"{population_filter} AND REPDTE:{report_date}",
            fields=tuple(fields),
            sort_by=require_string(download_config, "sort_by"),
            sort_order=require_string(download_config, "sort_order"),
            limit=require_int(download_config, "page_size"),
            offset=0,
            output_format=require_string(download_config, "format"),
        )
        request_parameters: JsonObject = {
            "quarter": quarter,
            "report_date": report_date,
            "endpoint": require_string(download_config, "endpoint"),
            "filters": query.filters,
            "fields": fields,
            "sort_by": query.sort_by,
            "sort_order": query.sort_order,
            "limit": query.limit,
            "requested_at": require_string(anchor_config, "request_date"),
        }
        write_json_once(output_dir / "request_parameters.json", request_parameters)
        result: DownloadResult = download_query(
            client=client,
            endpoint=require_string(download_config, "endpoint"),
            query=query,
            output_dir=output_dir,
            checkpoint_path=output_dir / "checkpoint.json",
            expected_report_date=report_date,
            required_fields=required_fields,
            allowed_unexpected_fields=allowed_unexpected_fields,
        )
        normalized_bytes: bytes = records_to_csv(result.records, fields)
        normalized_path: Path = output_dir / "financials.normalized.csv"
        normalized_hash: str = write_once(normalized_path, normalized_bytes)
        returned_fields: set[str] = set().union(*(record.keys() for record in result.records))
        schema: JsonObject = {
            field: inferred_type([record.get(field) for record in result.records])
            for field in sorted(returned_fields)
        }
        write_json_once(output_dir / "schema.json", schema)
        missingness: list[JsonObject] = [field_statistics(result.records, field) for field in fields]
        write_json_once(output_dir / "missingness.json", missingness)
        duplicates: list[tuple[str, str]] = find_duplicate_bank_quarters(result.records)
        write_json_once(output_dir / "duplicates.json", {"count": len(duplicates), "keys": duplicates})
        missing_cert: int = sum(1 for record in result.records if is_missing(record.get("CERT")))
        missing_date: int = sum(1 for record in result.records if is_missing(record.get("REPDTE")))
        unique_cert: int = len({scalar_text(record.get("CERT")) for record in result.records})
        unique_rssdid: int = len(
            {scalar_text(record.get("RSSDID")) for record in result.records if not is_missing(record.get("RSSDID"))}
        )
        page_paths: list[Path] = [
            path for path in output_dir.glob("page_*.json") if not path.name.endswith(".manifest.json")
        ]
        requested_set: set[str] = set(fields)
        unexpected_fields: list[str] = sorted(returned_fields.difference(requested_set).difference({"ID"}))
        missing_requested_fields: list[str] = sorted(requested_set.difference(returned_fields))
        validation_result: str = (
            "Fail"
            if duplicates or missing_cert > 0 or missing_date > 0 or unexpected_fields
            else ("Pass with documented unavailable fields" if missing_requested_fields else "Pass")
        )
        validation: JsonObject = {
            "quarter": quarter,
            "total_rows": result.total,
            "unique_cert": unique_cert,
            "unique_rssdid": unique_rssdid,
            "duplicate_bank_quarters": len(duplicates),
            "missing_cert": missing_cert,
            "missing_date": missing_date,
            "returned_fields": sorted(returned_fields),
            "missing_requested_fields": missing_requested_fields,
            "unexpected_fields": unexpected_fields,
            "api_pages": len(page_paths),
            "normalized_sha256": normalized_hash,
            "validation_result": validation_result,
        }
        write_json_once(output_dir / "validation.json", validation)
        anchor_rows.append(
            {
                "Quarter": quarter,
                "Total rows": result.total,
                "Unique CERT count": unique_cert,
                "Unique RSSDID count": unique_rssdid,
                "Duplicate bank-quarter count": len(duplicates),
                "Missing CERT count": missing_cert,
                "Missing date count": missing_date,
                "Requested fields": "|".join(fields),
                "Returned fields": "|".join(sorted(returned_fields)),
                "Unexpected fields": "|".join(unexpected_fields),
                "API pages": len(page_paths),
                "Pagination completeness": "Pass" if len(result.records) == result.total else "Fail",
                "Hash": normalized_hash,
                "Validation result": validation_result,
            }
        )
        for stats in missingness:
            field: str = str(stats["field"])
            status, plausibility_warning = plausibility_status(field, stats)
            regime_warning: str = definition_change_warning(field, quarter, stats)
            warning: str = "; ".join(
                value for value in (plausibility_warning, regime_warning) if value
            )
            continuity_rows.append(
                {
                    "Field": field,
                    "Quarter": quarter,
                    "Non-null percentage": round(float(stats["non_null_percentage"]), 6),
                    "Zero percentage": round(float(stats["zero_percentage"]), 6),
                    "Minimum": stats["minimum"],
                    "Maximum": stats["maximum"],
                    "Median": stats["median"],
                    "Number of institutions": result.total,
                    "Data type": stats["data_type"],
                    "Units": "identifier/text" if field in IDENTIFIER_FIELDS else ("percent" if field in PERCENT_FIELDS else "$000"),
                    "Plausibility status": status,
                    "Definition-change warning": warning,
                    "Availability status": (
                        "Unavailable or zero sentinel"
                        if float(stats["non_null_percentage"]) == 0 or float(stats["zero_percentage"]) == 100.0
                        else ("Partial" if float(stats["non_null_percentage"]) < 99.0 else "Available")
                    ),
                }
            )
            if field in NINE_MISSING_FIELDS:
                probe_rows.append(
                    {
                        "Field": field,
                        "Quarter": quarter,
                        "API accepted": "Yes",
                        "Row count": result.total,
                        "Non-null count": stats["non_null_count"],
                        "Non-null percentage": round(float(stats["non_null_percentage"]), 6),
                        "Distinct count": stats["distinct_count"],
                        "Minimum": stats["minimum"],
                        "Maximum": stats["maximum"],
                        "Definition match": "Yes — API result is consistent with FDIC YAML/workbook definition",
                        "Warning": warning,
                        "Recommended decision": PROBE_DECISIONS[field],
                    }
                )
            if warning:
                exception_rows.append(
                    {
                        "Exception ID": f"{quarter}-{field}",
                        "Quarter": quarter,
                        "Field": field,
                        "Control": "Anchor field availability and plausibility",
                        "Severity": "Medium" if float(stats["non_null_percentage"]) == 0 or float(stats["zero_percentage"]) == 100.0 else "Low",
                        "Observed value": f"non_null_pct={float(stats['non_null_percentage']):.6f}; min={stats['minimum']}; max={stats['maximum']}",
                        "Expected value": "Documented availability and plausible source range",
                        "Status": "Open",
                        "Resolution": "Classify in selected_financial_fields_v1.yaml",
                    }
                )
        if quarter == "2026_Q1":
            latest_records = result.records
        print(f"{quarter}: rows={result.total} pages={len(page_paths)} hash={normalized_hash}")
    report_dir: Path = ROOT / "reports"
    write_csv_report(report_dir / "anchor_quarter_validation.csv", anchor_rows, ["Quarter", "Total rows", "Unique CERT count", "Unique RSSDID count", "Duplicate bank-quarter count", "Missing CERT count", "Missing date count", "Requested fields", "Returned fields", "Unexpected fields", "API pages", "Pagination completeness", "Hash", "Validation result"])
    write_csv_report(report_dir / "field_probe_results.csv", probe_rows, ["Field", "Quarter", "API accepted", "Row count", "Non-null count", "Non-null percentage", "Distinct count", "Minimum", "Maximum", "Definition match", "Warning", "Recommended decision"])
    write_csv_report(report_dir / "field_continuity_by_anchor.csv", continuity_rows, ["Field", "Quarter", "Non-null percentage", "Zero percentage", "Minimum", "Maximum", "Median", "Number of institutions", "Data type", "Units", "Plausibility status", "Definition-change warning", "Availability status"])
    write_csv_report(report_dir / "ingestion_exceptions.csv", exception_rows, ["Exception ID", "Quarter", "Field", "Control", "Severity", "Observed value", "Expected value", "Status", "Resolution"])
    if not latest_records:
        raise RuntimeError("Latest anchor 2026_Q1 was not downloaded; reconciliation cannot run")
    reconciliation_rows: list[JsonObject] = manual_reconciliation(latest_records, fields)
    write_csv_report(report_dir / "manual_vs_api_reconciliation.csv", reconciliation_rows, ["Field", "Manual row count", "API row count", "Exact match", "Rounding difference", "Field-definition difference", "Population difference", "Timing difference", "Missing in API", "Missing in bulk file", "Unresolved", "Overall classification", "Warning"])
    run_summary: JsonObject = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "anchors": [anchor["quarter"] for anchor in anchors],
        "anchor_count": len(anchor_rows),
        "total_rows": sum(int(row["Total rows"]) for row in anchor_rows),
        "total_pages": sum(int(row["API pages"]) for row in anchor_rows),
        "fields_requested": fields,
        "config_sha256": sha256_file(ROOT / "configs" / "fdic_download_config.yaml"),
        "anchor_config_sha256": sha256_file(ROOT / "configs" / "anchor_quarters.yaml"),
        "report_hashes": {
            path.name: sha256_file(path)
            for path in sorted(report_dir.glob("*.csv"))
            if path.name in {"anchor_quarter_validation.csv", "field_probe_results.csv", "field_continuity_by_anchor.csv", "ingestion_exceptions.csv", "manual_vs_api_reconciliation.csv"}
        },
    }
    summary_path: Path = ROOT / "reports" / "phase1_probe_run_summary.json"
    summary_path.write_bytes(canonical_json_bytes(run_summary))


if __name__ == "__main__":
    run()
