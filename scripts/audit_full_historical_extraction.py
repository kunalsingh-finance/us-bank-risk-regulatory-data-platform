"""Independently verify the completed Phase 1B archive and combined panel."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.full_history import (  # noqa: E402
    LINEAGE_FIELDS,
    JsonObject,
    completion_marker_is_valid,
    configuration_hash,
    generate_quarters,
    validate_core_contract,
    verify_page_manifests,
)
from src.ingestion.manifest import sha256_file, write_replaceable_json  # noqa: E402


PHASE0_HASHES: dict[str, str] = {
    "data/raw/fdic_institutions_current.csv": "fd2c23f1294dfa001507e0f717375ce7f45f568c49fe2c15143587d9e263ff1b",
    "data/raw/fdic_institutions_definitions.csv": "1abbf82dda4c1c521d85a0008409d02da44f02c5835560857a5dd604dda06d62",
    "data/raw/fdic_financials_sample_2026_q1.csv": "574b8107643b4d6187ab4e9c84eba85c964bfc88edce0ed5089f30aaf638d782",
    "data/raw/fdic_failed_banks_2000_2026.csv": "9b65cfcc4177c5e2d7aa9f58a95091e5097079debfcbd83e8e0aafc0ebeb6bc1",
    "data/raw/fdic_history_events_2000_2026.csv": "f5debb448fdb63cf37b2960a06427e7cbf81dac1954fb4c8c47434d57afeeb98",
    "data/raw/fdic_history_events_definitions.csv": "fb2cc2f845e20d98ca873ef7ed5f9deb296c2c23f9e939e3b7203414d93cf914",
    "data/raw/definitions/fdic_institution_api_definitions.yaml": "3feca8d6d0d05de0640bdd9714db0ab5e9a882ebb0df634153155da3e9b8512b",
    "data/raw/definitions/fdic_failure_api_definitions.yaml": "7e3137fb6fc93dd49371b4d032f48fad403efd3d9a7f5cc8ca5480c00807364c",
    "data/raw/definitions/fdic_history_api_definitions.yaml": "a2b5fd8301aca26cdb813fdcb1ecf89d87d0040ffffa42c6af2f80adf8e1188e",
    "data/raw/definitions/fdic_financial_api_definitions.yaml": "588b5391f860099f91818f2eb52d3095fbb9d92beac32d05757acab01c53f732",
    "data/raw/definitions/fdic_common_financial_reports.xlsx": "6413c93064c16c63d4850221b25181f03ea51d086cd8f68d365cb070f383ab65",
}


class IntegrityAuditError(RuntimeError):
    """Raised when any independent Phase 1B integrity check fails."""


def load_object(path: Path) -> JsonObject:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrityAuditError(f"Expected JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def run() -> None:
    config_path: Path = ROOT / "configs" / "full_historical_extraction.yaml"
    config: JsonObject = load_object(config_path)
    stored_config_hash: object = config.get("configuration_hash")
    calculated_config_hash: str = configuration_hash(
        {key: value for key, value in config.items() if key != "configuration_hash"}
    )
    if stored_config_hash != calculated_config_hash:
        raise IntegrityAuditError(
            f"Configuration hash mismatch: stored={stored_config_hash}, calculated={calculated_config_hash}"
        )
    contract: JsonObject = load_object(ROOT / "configs" / "selected_financial_fields_v1.yaml")
    core_fields: tuple[str, ...] = validate_core_contract(contract)
    quarters = generate_quarters(str(config["start_quarter"]), str(config["end_quarter"]))
    page_count: int = 0
    page_row_total: int = 0
    quarter_row_total: int = 0
    retry_pages: int = 0
    retry_quarters: set[str] = set()
    for quarter in quarters:
        output_dir: Path = ROOT / "data" / "raw" / "api" / "financials" / quarter.label / "core_v1"
        marker_path: Path = output_dir / "quarter_complete.json"
        if not completion_marker_is_valid(marker_path, calculated_config_hash):
            raise IntegrityAuditError(f"Invalid completion marker: quarter={quarter.label}")
        marker: JsonObject = load_object(marker_path)
        observed_pages, observed_rows = verify_page_manifests(output_dir)
        if marker.get("page_count") != observed_pages or marker.get("row_count") != observed_rows:
            raise IntegrityAuditError(
                f"Quarter page/row reconciliation failed: quarter={quarter.label}, "
                f"marker_pages={marker.get('page_count')}, observed_pages={observed_pages}, "
                f"marker_rows={marker.get('row_count')}, observed_rows={observed_rows}"
            )
        raw_path: Path = output_dir / "financials.combined.jsonl"
        source_normalized_path: Path = output_dir / "financials.normalized.csv"
        interim_path: Path = ROOT / "data" / "interim" / "financials_by_quarter" / f"{quarter.label}.normalized.csv"
        hash_controls: tuple[tuple[Path, object], ...] = (
            (raw_path, marker.get("quarter_raw_sha256")),
            (source_normalized_path, marker.get("source_normalized_sha256")),
            (interim_path, marker.get("interim_normalized_sha256")),
        )
        for path, expected_hash in hash_controls:
            if not path.exists() or sha256_file(path) != expected_hash:
                raise IntegrityAuditError(
                    f"Quarter final-file hash mismatch: quarter={quarter.label}, path={path}"
                )
        for manifest_path in output_dir.glob("page_*.manifest.json"):
            page_manifest: JsonObject = load_object(manifest_path)
            attempts: object = page_manifest.get("attempts")
            if isinstance(attempts, int) and attempts > 1:
                retry_pages += 1
                retry_quarters.add(quarter.label)
        page_count += observed_pages
        page_row_total += observed_rows
        quarter_row_total += int(marker["row_count"])
    if page_row_total != quarter_row_total:
        raise IntegrityAuditError(
            f"Archive row totals differ: page_rows={page_row_total}, quarter_rows={quarter_row_total}"
        )
    parquet_path: Path = ROOT / "data" / "processed" / "ingestion_stage" / "fdic_financials_2001q1_2026q1.parquet"
    table = pq.read_table(parquet_path)
    expected_columns: tuple[str, ...] = (*core_fields, *LINEAGE_FIELDS)
    if tuple(table.column_names) != expected_columns:
        raise IntegrityAuditError(
            f"Combined schema differs: expected={expected_columns}, observed={tuple(table.column_names)}"
        )
    row_count: int = table.num_rows
    if row_count != quarter_row_total:
        raise IntegrityAuditError(
            f"Combined row count differs: parquet={row_count}, quarters={quarter_row_total}"
        )
    certs: list[str | None] = table.column("CERT").to_pylist()
    report_dates: list[str | None] = table.column("REPDTE").to_pylist()
    keys: list[tuple[str | None, str | None]] = list(zip(certs, report_dates, strict=True))
    duplicate_count: int = len(keys) - len(set(keys))
    if duplicate_count != 0:
        raise IntegrityAuditError(f"Combined bank-quarter duplicate count is {duplicate_count}")
    observed_dates: set[str] = {str(value) for value in report_dates if value is not None}
    expected_dates: set[str] = {quarter.report_date for quarter in quarters}
    if observed_dates != expected_dates:
        raise IntegrityAuditError(
            f"Combined report dates differ: missing={sorted(expected_dates - observed_dates)}, "
            f"unexpected={sorted(observed_dates - expected_dates)}"
        )
    phase0_failures: list[str] = [
        path for path, expected_hash in PHASE0_HASHES.items() if sha256_file(ROOT / path) != expected_hash
    ]
    if phase0_failures:
        raise IntegrityAuditError(f"Phase 0 immutable source failures: {phase0_failures}")
    anchor_page_count: int = 0
    anchor_failures: list[str] = []
    for path in (ROOT / "data" / "raw" / "api" / "financials").glob("*_Q*/page_*.manifest.json"):
        anchor_page_count += 1
        manifest: JsonObject = load_object(path)
        raw_path = path.with_name(path.name.replace(".manifest.json", ".json"))
        if not raw_path.exists() or sha256_file(raw_path) != manifest.get("response_sha256"):
            anchor_failures.append(str(raw_path))
    if anchor_failures:
        raise IntegrityAuditError(f"Phase 1 anchor page failures: {anchor_failures}")
    run_manifest: JsonObject = load_object(
        ROOT / "manifests" / "full_historical_extraction" / "run_manifest.json"
    )
    parquet_hash: str = sha256_file(parquet_path)
    if run_manifest.get("combined_panel_sha256") != parquet_hash:
        raise IntegrityAuditError("Run manifest combined-panel hash does not match Parquet")
    audit: JsonObject = {
        "status": "PASS",
        "configuration_hash": calculated_config_hash,
        "expected_quarters": len(quarters),
        "completed_quarters": len(quarters),
        "page_count": page_count,
        "page_row_total": page_row_total,
        "quarter_row_total": quarter_row_total,
        "combined_row_count": row_count,
        "combined_column_count": len(expected_columns),
        "combined_duplicate_bank_quarters": duplicate_count,
        "unique_cert_count": len({value for value in certs if value is not None}),
        "earliest_report_date": min(observed_dates),
        "latest_report_date": max(observed_dates),
        "combined_panel_sha256": parquet_hash,
        "phase0_files_verified": len(PHASE0_HASHES),
        "phase0_hash_failures": 0,
        "phase1_anchor_pages_verified": anchor_page_count,
        "phase1_anchor_hash_failures": 0,
        "retried_pages": retry_pages,
        "retried_quarters": sorted(retry_quarters),
        "financial_values_imputed": False,
        "risk_ratios_calculated": False,
        "labels_created": False,
        "modelling_performed": False,
    }
    output_path: Path = ROOT / "manifests" / "full_historical_extraction" / "integrity_audit.json"
    write_replaceable_json(output_path, audit)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    run()
