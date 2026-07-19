"""Create the frozen, self-hashed Phase 2 database build configuration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, configuration_hash, write_replaceable_json  # noqa: E402


def build_configuration() -> JsonObject:
    config: JsonObject = {
        "phase": "Phase 2 SQL Data Modelling and Reconciliation",
        "run_id": "phase2-20260716t215215z",
        "build_timestamp": "2026-07-16T21:52:15Z",
        "build_version": "phase2-1.0.0",
        "schema_version": "bank-risk-sql-v1",
        "database_path": "database/bank_risk.duckdb",
        "input_sources": [
            {"name": "financials", "path": "data/processed/ingestion_stage/fdic_financials_2001q1_2026q1.parquet", "sha256": "94d360d8e39c86658350e5b981d389e0d4c3c48376dc89adaa223caf6ef0232c", "expected_rows": 698804},
            {"name": "institutions", "path": "data/raw/fdic_institutions_current.csv", "sha256": "fd2c23f1294dfa001507e0f717375ce7f45f568c49fe2c15143587d9e263ff1b", "expected_rows": 27836},
            {"name": "history_events", "path": "data/raw/fdic_history_events_2000_2026.csv", "sha256": "f5debb448fdb63cf37b2960a06427e7cbf81dac1954fb4c8c47434d57afeeb98", "expected_rows": 352107},
            {"name": "failures", "path": "data/raw/fdic_failed_banks_2000_2026.csv", "sha256": "9b65cfcc4177c5e2d7aa9f58a95091e5097079debfcbd83e8e0aafc0ebeb6bc1", "expected_rows": 592},
        ],
        "expected_date_coverage": {"start": "2001-03-31", "end": "2026-03-31", "quarters": 101},
        "required_fields": [
            "CERT", "RSSDID", "NAMEFULL", "REPDTE", "STALP", "BKCLASS", "REGAGNT", "ACTIVE", "ASSET",
            "EQ", "EQTOT", "LNLSGR", "LNLSNET", "P3ASSET", "P9ASSET", "NAASSET", "ORE", "CHBAL", "SC",
            "DEP", "DEPDOM", "DEPCSBQ", "FREPO", "OTHBFHLB", "LNRECONS", "LNREMULT", "LNRERES", "LNCI",
            "LNCON", "LNCRCD", "NIMQ", "NIMYQ", "NETINCQ", "NONIIQ", "NONIXQ", "PTAXNETINCQ", "ROAQ",
            "EEFFQR", "INTEXPYQ", "NTLNLSQ",
        ],
        "identifier_rules": {"primary_institution_identifier": "CERT", "secondary_identifier": "RSSDID", "bank_quarter_key": ["CERT", "reporting_date"], "reporting_date_rule": "calendar quarter end"},
        "table_list": [
            "staging.financials", "staging.institutions", "staging.history_events", "staging.failures", "staging.identifier_crosswalk",
            "core.institutions", "core.bank_quarter_financials", "core.institution_history_events", "core.bank_failures_reference", "core.bank_exits_reference",
            "quality.data_quality_exceptions", "quality.control_results", "quality.unmatched_identifiers", "quality.duplicate_candidates", "quality.schema_validation_results",
        ],
        "sql_execution_order": [
            "sql/001_create_schemas.sql", "sql/002_create_ingestion_metadata.sql", "sql/003_load_financials_stage.sql", "sql/004_load_institutions_stage.sql", "sql/005_load_history_stage.sql", "sql/006_load_failures_stage.sql", "sql/007_standardize_identifiers.sql", "sql/008_build_institution_dimension.sql", "sql/009_build_bank_quarter_fact.sql", "sql/010_build_history_events.sql", "sql/011_build_failure_reference.sql", "sql/012_build_source_lineage.sql", "sql/013_run_data_quality_controls.sql", "sql/014_build_reconciliation_views.sql", "sql/015_create_public_views.sql",
        ],
        "validation_thresholds": {"deposit_asset_multiple": 1.5, "percentage_abs_bound": 100.0},
        "overwrite_policy": "build transactionally in an owned temporary file and replace only after all blocking validations pass",
        "generated_database_policy": "git-ignored and reproducibly rebuilt",
    }
    config["configuration_hash"] = configuration_hash(config)
    return config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    digest: str = write_replaceable_json(arguments.output, build_configuration())
    print(f"Wrote {arguments.output} (file_sha256={digest})")


if __name__ == "__main__":
    main()
