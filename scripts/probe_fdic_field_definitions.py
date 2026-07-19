"""Probe disputed FDIC fields on the approved anchors only."""

from __future__ import annotations

import csv
import io
import json
import math
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.downloader import download_query  # noqa: E402
from src.ingestion.fdic_client import FdicClient, FdicClientConfig, FinancialsQuery  # noqa: E402
from src.ingestion.manifest import write_once  # noqa: E402
from src.ingestion.schema import Record, Scalar  # noqa: E402


PROBE_FIELDS: tuple[str, ...] = (
    "CERT",
    "REPDTE",
    "ASSET",
    "EQ",
    "EQV",
    "NIM",
    "NIMQ",
    "NIMY",
    "NIMYQ",
    "NIMA",
    "ERNAST5",
    "INTINC",
    "EINTEXP",
    "DEPUNINS",
    "DEPUNA",
    "CBLRIND",
    "RBC1AAJ",
    "IDT1CER",
    "IDT1RWAJR",
    "RBCRWAJ",
)


def load_object(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return {str(key): item for key, item in value.items()}


def text(value: object) -> str:
    return "" if value is None else str(value)


def number(value: Scalar) -> float | None:
    if value is None or isinstance(value, bool) or text(value).strip().lower() in {"", "null"}:
        return None
    try:
        parsed: float = float(text(value))
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def records_csv(records: list[Record]) -> bytes:
    output = io.StringIO(newline="")
    fields: list[str] = [*PROBE_FIELDS, "ID"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for record in sorted(records, key=lambda row: int(text(row["CERT"]))):
        writer.writerow({field: text(record.get(field)) for field in fields})
    return output.getvalue().encode("utf-8")


def comparison_summary(records: list[Record], quarter: str) -> list[dict[str, object]]:
    eqv_errors: list[float] = []
    nim_errors: list[float] = []
    nimy_errors: list[float] = []
    nim_vs_quarterly_compared: int = 0
    nim_vs_quarterly_equal: int = 0
    margin_vs_quarterly_compared: int = 0
    margin_vs_quarterly_equal: int = 0
    dep_equal: int = 0
    dep_compared: int = 0
    depunins_non_null: int = 0
    depuna_non_null: int = 0
    cblr_one: int = 0
    cblr_zero: int = 0
    cblr_other: int = 0
    for record in records:
        asset = number(record.get("ASSET"))
        equity = number(record.get("EQ"))
        eqv = number(record.get("EQV"))
        if asset not in {None, 0.0} and equity is not None and eqv is not None:
            eqv_errors.append(abs(eqv - 100.0 * equity / asset))
        nim = number(record.get("NIM"))
        interest_income = number(record.get("INTINC"))
        interest_expense = number(record.get("EINTEXP"))
        if nim is not None and interest_income is not None and interest_expense is not None:
            nim_errors.append(abs(nim - (interest_income - interest_expense)))
        nimq = number(record.get("NIMQ"))
        if nim is not None and nimq is not None:
            nim_vs_quarterly_compared += 1
            nim_vs_quarterly_equal += int(nim == nimq)
        nimy = number(record.get("NIMY"))
        nimyq = number(record.get("NIMYQ"))
        if nimy is not None and nimyq is not None:
            margin_vs_quarterly_compared += 1
            margin_vs_quarterly_equal += int(abs(nimy - nimyq) <= 0.0050000001)
        nima = number(record.get("NIMA"))
        earning_assets = number(record.get("ERNAST5"))
        if nimy is not None and nima is not None and earning_assets not in {None, 0.0}:
            nimy_errors.append(abs(nimy - 100.0 * nima / earning_assets))
        depunins = number(record.get("DEPUNINS"))
        depuna = number(record.get("DEPUNA"))
        depunins_non_null += int(depunins is not None)
        depuna_non_null += int(depuna is not None)
        if depunins is not None and depuna is not None:
            dep_compared += 1
            dep_equal += int(depunins == depuna)
        cblr = number(record.get("CBLRIND"))
        if cblr == 1.0:
            cblr_one += 1
        elif cblr == 0.0:
            cblr_zero += 1
        else:
            cblr_other += 1
    total: int = len(records)
    return [
        {"Quarter": quarter, "Control": "EQV equals 100 * EQ / ASSET", "Compared rows": len(eqv_errors), "Exact rows": sum(error <= 1e-10 for error in eqv_errors), "Maximum absolute difference": max(eqv_errors) if eqv_errors else "", "Result": "Pass" if eqv_errors and max(eqv_errors) <= 1e-10 else "Review"},
        {"Quarter": quarter, "Control": "NIM equals INTINC minus EINTEXP", "Compared rows": len(nim_errors), "Exact rows": sum(error <= 1e-10 for error in nim_errors), "Maximum absolute difference": max(nim_errors) if nim_errors else "", "Result": "Pass" if nim_errors and max(nim_errors) <= 1e-10 else "Review"},
        {"Quarter": quarter, "Control": "NIMY equals 100 * NIMA / ERNAST5", "Compared rows": len(nimy_errors), "Exact rows": sum(error <= 1e-10 for error in nimy_errors), "Maximum absolute difference": max(nimy_errors) if nimy_errors else "", "Result": "Pass" if nimy_errors and max(nimy_errors) <= 1e-10 else "Review"},
        {"Quarter": quarter, "Control": "NIM YTD equals NIMQ quarterly", "Compared rows": nim_vs_quarterly_compared, "Exact rows": nim_vs_quarterly_equal, "Maximum absolute difference": "", "Result": "Expected equal only in first quarter"},
        {"Quarter": quarter, "Control": "NIMY YTD margin equals NIMYQ quarterly margin within source rounding", "Compared rows": margin_vs_quarterly_compared, "Exact rows": margin_vs_quarterly_equal, "Maximum absolute difference": "", "Result": "Expected equal only in first quarter"},
        {"Quarter": quarter, "Control": "DEPUNINS equals DEPUNA where both reported", "Compared rows": dep_compared, "Exact rows": dep_equal, "Maximum absolute difference": "", "Result": "Pass" if dep_compared > 0 and dep_equal == dep_compared else "Review"},
        {"Quarter": quarter, "Control": "DEPUNINS non-null population", "Compared rows": total, "Exact rows": depunins_non_null, "Maximum absolute difference": "", "Result": f"{depunins_non_null}/{total}"},
        {"Quarter": quarter, "Control": "DEPUNA non-null population", "Compared rows": total, "Exact rows": depuna_non_null, "Maximum absolute difference": "", "Result": f"{depuna_non_null}/{total}"},
        {"Quarter": quarter, "Control": "CBLRIND distribution", "Compared rows": total, "Exact rows": cblr_one, "Maximum absolute difference": "", "Result": f"one={cblr_one}; zero={cblr_zero}; other_or_missing={cblr_other}"},
    ]


def run() -> None:
    config = load_object(ROOT / "configs" / "fdic_download_config.yaml")
    anchors = load_object(ROOT / "configs" / "anchor_quarters.yaml")
    required = frozenset(str(value) for value in config["required_fields"])
    allowed = frozenset(str(value) for value in config["allowed_unexpected_fields"])
    client = FdicClient.live(
        FdicClientConfig(
            base_url=str(config["base_url"]),
            timeout_seconds=int(config["timeout_seconds"]),
            max_attempts=int(config["max_attempts"]),
            backoff_base_seconds=float(config["backoff_base_seconds"]),
            user_agent=str(config["user_agent"]),
            allowed_unexpected_fields=allowed,
            required_fields=required,
        )
    )
    rows: list[dict[str, object]] = []
    anchor_values: object = anchors["anchors"]
    if not isinstance(anchor_values, list):
        raise ValueError("anchors must be an array")
    for anchor_value in anchor_values:
        if not isinstance(anchor_value, dict):
            raise ValueError("anchor must be an object")
        quarter: str = str(anchor_value["quarter"])
        report_date: str = str(anchor_value["report_date"])
        output_dir: Path = ROOT / "data" / "raw" / "api" / "field_resolution_v2" / quarter
        query = FinancialsQuery(
            filters=f"{config['population_filter']} AND REPDTE:{report_date}",
            fields=PROBE_FIELDS,
            sort_by=str(config["sort_by"]),
            sort_order=str(config["sort_order"]),
            limit=10000,
            offset=0,
            output_format=str(config["format"]),
        )
        result = download_query(client, str(config["endpoint"]), query, output_dir, output_dir / "checkpoint.json", report_date, required, allowed)
        write_once(output_dir / "field_resolution.normalized.csv", records_csv(result.records))
        rows.extend(comparison_summary(result.records, quarter))
        print(f"{quarter}: rows={result.total}")
    report_path: Path = ROOT / "reports" / "field_definition_probe.csv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        columns: list[str] = ["Quarter", "Control", "Compared rows", "Exact rows", "Maximum absolute difference", "Result"]
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
