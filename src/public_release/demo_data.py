"""Build deterministic synthetic dashboard data for the public demonstration."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Final

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.database.manifest import sha256_file

DEMO_BUILD_RUN_ID: Final[str] = "public-demo-v1-20260719"
DEMO_CONFIGURATION_HASH: Final[str] = "e11e6cd5f9f992cfae3ea852eee984bb24e84ec37a0ddd7ab9154987cb833d39"
FROZEN_MODEL_VERSION: Final[str] = "hist_gradient_boosting__1"
FROZEN_PREDICTION_SOURCE_HASH: Final[str] = "a57c8e00240f389fafa36d8440bc53494c916d8c4b4098b9eb7d17aea2078cc2"
DEMO_BUILD_TIMESTAMP: Final[str] = "2026-07-19T00:00:00Z"
SOURCE_LINEAGE: Final[str] = "Deterministic synthetic institution records; frozen aggregate Phase 5 validation evidence"
VALIDATION_STATUS: Final[str] = "DEMONSTRATION_ONLY"
PROTOCOL_HASH: Final[str] = "f327147658facf9f2d9f80f2270081a16e010b99d6c73b7ca3ee283aa4c00cf4"
ASSET_BANDS: Final[tuple[str, ...]] = ("LT_100M", "100M_500M", "500M_1B", "1B_10B", "10B_50B", "50B_250B", "GT_250B")
BANK_CLASSES: Final[tuple[str, ...]] = ("NM", "SM", "N", "SA")
DRIVER_FEATURES: Final[tuple[str, ...]] = (
    "equity_to_assets",
    "return_on_equity",
    "past_due_30_89_to_total_loans",
    "loans_to_deposits",
    "total_loan_growth_yoy_pct",
    "loan_concentration_hhi",
)


def metadata_columns() -> dict[str, object]:
    return {
        "dashboard_build_run_id": DEMO_BUILD_RUN_ID,
        "dashboard_configuration_hash": DEMO_CONFIGURATION_HASH,
        "frozen_model_version": FROZEN_MODEL_VERSION,
        "prediction_source_hash": FROZEN_PREDICTION_SOURCE_HASH,
        "source_lineage": SOURCE_LINEAGE,
        "build_timestamp": DEMO_BUILD_TIMESTAMP,
        "validation_status": VALIDATION_STATUS,
    }


def reporting_dates() -> tuple[pd.Timestamp, ...]:
    return tuple(pd.Timestamp(value) for value in pd.date_range("2023-03-31", "2024-12-31", freq="QE-DEC"))


def risk_tier(percentile: float) -> str:
    if percentile >= 99.0:
        return "Highest monitored tier"
    if percentile >= 95.0:
        return "High"
    if percentile >= 90.0:
        return "Elevated"
    if percentile >= 75.0:
        return "Moderate"
    return "Low"


def synthetic_score(bank_number: int, quarter_number: int) -> float:
    cycle: float = 0.08 * math.sin((bank_number + quarter_number * 3) / 7.0)
    trend: float = ((bank_number * 37 + quarter_number * 61) % 997) / 997.0
    return float(min(0.995, max(0.005, 0.82 * trend + 0.18 * (cycle + 0.5))))


def feature_values(score: float, bank_number: int, quarter_number: int) -> dict[str, float]:
    wave: float = math.sin((bank_number + quarter_number) / 8.0)
    equity_to_assets: float = 13.5 - 6.0 * score + 0.35 * wave
    return {
        "equity_to_assets": equity_to_assets,
        "equity_change_yoy_pct": -12.0 * score + 2.0 * wave,
        "noncurrent_assets_to_total_loans": 0.35 + 4.4 * score + 0.2 * wave,
        "past_due_30_89_to_total_loans": 0.45 + 2.5 * score + 0.15 * wave,
        "return_on_assets": 1.45 - 2.2 * score + 0.1 * wave,
        "return_on_equity": 12.0 - 20.0 * score + 0.8 * wave,
        "net_interest_margin": 3.6 - 0.8 * score + 0.1 * wave,
        "efficiency_ratio": 52.0 + 37.0 * score + 1.5 * wave,
        "liquid_assets_to_total_assets": 28.0 - 15.0 * score + 0.7 * wave,
        "loans_to_deposits": 61.0 + 47.0 * score + 1.8 * wave,
        "deposits_to_total_assets": 87.0 - 17.0 * score + 0.8 * wave,
        "fhlb_advances_to_total_assets": 0.8 + 10.0 * score + 0.4 * wave,
        "deposit_growth_yoy_pct": 8.0 - 16.0 * score + 1.5 * wave,
        "funding_cost": 0.65 + 3.1 * score + 0.1 * wave,
        "loan_concentration_hhi": 0.17 + 0.32 * score + 0.01 * wave,
        "largest_reported_loan_category_share": 24.0 + 34.0 * score + 1.2 * wave,
        "total_asset_growth_yoy_pct": 5.0 + 19.0 * score + 1.5 * wave,
        "total_loan_growth_yoy_pct": 3.0 + 23.0 * score + 1.6 * wave,
        "loan_growth_minus_deposit_growth": -5.0 + 25.0 * score + 1.0 * wave,
    }


def build_score_rows(bank_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    dates: tuple[pd.Timestamp, ...] = reporting_dates()
    for quarter_number, reporting_date in enumerate(dates):
        quarter_rows: list[dict[str, object]] = []
        for bank_number in range(1, bank_count + 1):
            score: float = synthetic_score(bank_number, quarter_number)
            quarter_rows.append({
                "cert": 900000 + bank_number,
                "rssdid": 9900000 + bank_number,
                "reporting_date": reporting_date,
                "model_score": score,
                "historical_outcome": 0,
                "prediction_split": "SYNTHETIC_DEMO",
                "asset_size_band": ASSET_BANDS[(bank_number - 1) % len(ASSET_BANDS)],
                "bank_class": BANK_CLASSES[(bank_number - 1) % len(BANK_CLASSES)],
                "feature_quality_status": "PASS" if bank_number % 17 else "WARNING",
                "protocol_hash": PROTOCOL_HASH,
                "bank_name": f"Synthetic Bank {bank_number:03d}",
                "state": "DEMO",
            })
        ordered: list[dict[str, object]] = sorted(quarter_rows, key=lambda row: (-float(row["model_score"]), int(row["cert"])))
        for rank, row in enumerate(ordered, start=1):
            percentile: float = 100.0 * (bank_count - rank) / (bank_count - 1)
            prior_score: float = synthetic_score(int(row["cert"]) - 900000, max(0, quarter_number - 1))
            prior_rank_proxy: float = 100.0 * prior_score
            four_prior_score: float = synthetic_score(int(row["cert"]) - 900000, max(0, quarter_number - 4))
            row.update({
                "final_peer_group_id": f"{reporting_date.year}Q{reporting_date.quarter}|{row['asset_size_band']}|{row['bank_class']}",
                "final_peer_group_size": 25,
                "peer_group_method": "synthetic_demo_asset_band_and_class",
                "peer_benchmark_status": "PASS",
                "scored_population": bank_count,
                "same_quarter_rank": rank,
                "same_quarter_percentile": percentile,
                "top_1_percent_flag": percentile >= 99.0,
                "top_5_percent_flag": percentile >= 95.0,
                "top_10_percent_flag": percentile >= 90.0,
                "risk_tier": risk_tier(percentile),
                "prior_quarter_percentile": prior_rank_proxy if quarter_number >= 1 else None,
                "four_quarter_prior_percentile": 100.0 * four_prior_score if quarter_number >= 4 else None,
                "percentile_change_qoq": percentile - prior_rank_proxy if quarter_number >= 1 else None,
                "percentile_change_yoy": percentile - 100.0 * four_prior_score if quarter_number >= 4 else None,
                "out_of_sample_flag": True,
                "alert_status": "TOP_5_PERCENT_REVIEW" if percentile >= 95.0 else "NO_ALERT",
                "data_quality_warning": "Synthetic source-field warning" if row["feature_quality_status"] != "PASS" else "",
                "model_limitation_warning": "Synthetic ranking only; not a probability or institution-level prediction.",
                **metadata_columns(),
            })
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["reporting_date", "cert"], ignore_index=True)


def build_history(scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in scores.itertuples(index=False):
        quarter_number: int = reporting_dates().index(pd.Timestamp(row.reporting_date))
        bank_number: int = int(row.cert) - 900000
        score_row: dict[str, object] = row._asdict()
        history_row: dict[str, object] = {
            key: score_row[key]
            for key in (
                "cert", "rssdid", "bank_name", "state", "reporting_date", "asset_size_band", "bank_class",
                "model_score", "same_quarter_percentile", "same_quarter_rank", "scored_population", "risk_tier",
                "top_1_percent_flag", "top_5_percent_flag", "top_10_percent_flag", "prediction_split",
                "feature_quality_status", "peer_benchmark_status",
            )
        }
        history_row.update(feature_values(float(row.model_score), bank_number, quarter_number))
        history_row.update(metadata_columns())
        rows.append(history_row)
    return pd.DataFrame(rows).sort_values(["reporting_date", "cert"], ignore_index=True)


def build_peer_comparisons(history: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for reporting_date, quarter in history.groupby("reporting_date", sort=True):
        for feature in DRIVER_FEATURES:
            values: pd.Series = quarter[feature].astype(float)
            peer_mean: float = float(values.mean())
            peer_median: float = float(values.median())
            peer_p25: float = float(values.quantile(0.25))
            peer_p75: float = float(values.quantile(0.75))
            mad: float = float((values - peer_median).abs().median())
            for row in quarter.itertuples(index=False):
                feature_value: float = float(getattr(row, feature))
                bank_percentile: float = float((values <= feature_value).mean() * 100.0)
                rows.append({
                    "cert": int(row.cert), "rssdid": int(row.rssdid), "bank_name": str(row.bank_name), "state": str(row.state),
                    "reporting_date": pd.Timestamp(reporting_date), "asset_size_band": str(row.asset_size_band), "bank_class": str(row.bank_class),
                    "final_peer_group_id": str(row.final_peer_group_id) if hasattr(row, "final_peer_group_id") else f"DEMO|{row.asset_size_band}",
                    "peer_group_method": "synthetic_demo_same_quarter", "feature_name": feature, "feature_value": feature_value,
                    "peer_count": len(quarter), "peer_mean": peer_mean, "peer_median": peer_median, "peer_p25": peer_p25,
                    "peer_p75": peer_p75, "bank_percentile": bank_percentile, "risk_direction_adjusted_percentile": bank_percentile,
                    "difference_from_peer_median": feature_value - peer_median,
                    "robust_z_score": 0.6745 * (feature_value - peer_median) / mad if mad > 0 else 0.0,
                    "peer_feature_count_too_small": False, "peer_validation_status": "PASS", **metadata_columns(),
                })
    return pd.DataFrame(rows).sort_values(["reporting_date", "cert", "feature_name"], ignore_index=True)


def build_drivers(history: pd.DataFrame, peers: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in history.itertuples(index=False):
        selected: tuple[str, ...] = (
            DRIVER_FEATURES[(int(row.cert) + pd.Timestamp(row.reporting_date).quarter) % len(DRIVER_FEATURES)],
            DRIVER_FEATURES[(int(row.cert) + 2) % len(DRIVER_FEATURES)],
            DRIVER_FEATURES[(int(row.cert) + 4) % len(DRIVER_FEATURES)],
        )
        peer_rows: pd.DataFrame = peers.loc[(peers["cert"] == row.cert) & (peers["reporting_date"] == row.reporting_date)].set_index("feature_name")
        for driver_rank, feature in enumerate(selected, start=1):
            peer: pd.Series = peer_rows.loc[feature]
            current_value: float = float(getattr(row, feature))
            direction: str = "associated with a higher ranking" if float(peer["bank_percentile"]) >= 50.0 else "associated with a lower ranking"
            rows.append({
                "cert": int(row.cert), "rssdid": int(row.rssdid), "reporting_date": pd.Timestamp(row.reporting_date),
                "driver_rank": driver_rank, "feature_name": feature,
                "score_delta": abs(float(peer["bank_percentile"]) - 50.0) / 1000.0,
                "driver_direction": direction, "current_feature_value": current_value,
                "training_median_reference": float(peer["peer_median"]),
                "explanation_method": "synthetic demonstration association",
                "final_peer_group_id": f"DEMO|{row.asset_size_band}|{row.bank_class}",
                "peer_group_method": "synthetic_demo_same_quarter", "peer_count": int(peer["peer_count"]),
                "peer_median": float(peer["peer_median"]), "peer_p25": float(peer["peer_p25"]), "peer_p75": float(peer["peer_p75"]),
                "bank_percentile": float(peer["bank_percentile"]),
                "risk_direction_adjusted_percentile": float(peer["risk_direction_adjusted_percentile"]),
                "difference_from_peer_median": float(peer["difference_from_peer_median"]),
                "peer_feature_count_too_small": False, "peer_comparison_warning": "", **metadata_columns(),
            })
    return pd.DataFrame(rows).sort_values(["reporting_date", "cert", "driver_rank"], ignore_index=True)


def build_watchlist(scores: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    latest_date: pd.Timestamp = pd.Timestamp(scores["reporting_date"].max())
    selected: pd.DataFrame = scores.loc[(scores["reporting_date"] == latest_date) & scores["top_5_percent_flag"]].copy()
    driver_latest: pd.DataFrame = drivers.loc[drivers["reporting_date"] == latest_date]
    driver_wide: pd.DataFrame = driver_latest.pivot(index="cert", columns="driver_rank", values=["feature_name", "driver_direction", "current_feature_value", "difference_from_peer_median"])
    rows: list[dict[str, object]] = []
    for row in selected.itertuples(index=False):
        values: pd.Series = driver_wide.loc[row.cert]
        output: dict[str, object] = {
            key: row._asdict()[key]
            for key in (
                "cert", "rssdid", "bank_name", "state", "reporting_date", "asset_size_band", "bank_class", "model_score",
                "same_quarter_percentile", "same_quarter_rank", "scored_population", "risk_tier", "top_1_percent_flag",
                "top_5_percent_flag", "top_10_percent_flag", "percentile_change_qoq", "percentile_change_yoy", "alert_status",
                "prediction_split", "out_of_sample_flag", "feature_quality_status", "peer_benchmark_status",
                "data_quality_warning", "model_limitation_warning",
            )
        }
        for rank in (1, 2, 3):
            output[f"top_driver_{rank}"] = str(values[("feature_name", rank)])
            output[f"driver_direction_{rank}"] = str(values[("driver_direction", rank)])
            output[f"current_driver_value_{rank}"] = float(values[("current_feature_value", rank)])
            output[f"peer_comparison_{rank}"] = float(values[("difference_from_peer_median", rank)])
        output.update(metadata_columns())
        rows.append(output)
    return pd.DataFrame(rows).sort_values(["same_quarter_rank", "cert"], ignore_index=True)


def build_quality(scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in scores.itertuples(index=False):
        warning: bool = str(row.feature_quality_status) != "PASS"
        rows.append({
            "cert": int(row.cert), "rssdid": int(row.rssdid), "bank_name": str(row.bank_name), "reporting_date": pd.Timestamp(row.reporting_date),
            "feature_quality_status": str(row.feature_quality_status), "peer_benchmark_status": str(row.peer_benchmark_status),
            "missing_numerator_count": int(warning), "denominator_exception_count": 0, "missing_denominator_count": 0,
            "zero_denominator_count": 0, "negative_denominator_count": 0, "insufficient_lag_history": False,
            "peer_group_too_small": False, "extreme_preserved_value": False, "suspected_unit_issue": False,
            "identifier_continuity_concern": False, "source_field_quality_warning": warning,
            "data_quality_warning": "Synthetic demonstration warning" if warning else "", **metadata_columns(),
        })
    return pd.DataFrame(rows).sort_values(["reporting_date", "cert"], ignore_index=True)


def build_cases(scores: pd.DataFrame) -> pd.DataFrame:
    latest: pd.DataFrame = scores.loc[scores["reporting_date"] == scores["reporting_date"].max()].sort_values("same_quarter_rank")
    selections: tuple[tuple[str, int, bool, str], ...] = (
        ("Synthetic captured event", 0, True, "Synthetic scenario illustrating an event captured inside the top-5% review budget."),
        ("Synthetic missed event", 45, True, "Synthetic scenario illustrating a historical event outside the top-10% ranking."),
        ("Synthetic false alert", 2, False, "Synthetic scenario illustrating a high ranking without an observed event."),
        ("Synthetic stable comparator", 85, False, "Synthetic low-ranked comparison scenario."),
    )
    rows: list[dict[str, object]] = []
    for role, position, event, rationale in selections:
        source: pd.Series = latest.iloc[position]
        reporting_date: pd.Timestamp = pd.Timestamp(source["reporting_date"])
        failure_date: pd.Timestamp | pd.NaT = reporting_date + pd.Timedelta(days=180) if event else pd.NaT
        rows.append({
            "case_role": role, "selection_status": "SELECTED", "selection_rationale": rationale,
            "cert": int(source["cert"]), "rssdid": int(source["rssdid"]), "bank_name": str(source["bank_name"]), "state": "DEMO",
            "reporting_date": reporting_date, "failure_date": failure_date,
            "first_top_5_alert_date": reporting_date if bool(source["top_5_percent_flag"]) else pd.NaT,
            "lead_days_top_5": 180.0 if event and bool(source["top_5_percent_flag"]) else None,
            "same_quarter_percentile": float(source["same_quarter_percentile"]), "same_quarter_rank": int(source["same_quarter_rank"]),
            "asset_size_band": str(source["asset_size_band"]), "risk_tier": str(source["risk_tier"]),
            "captured_top_1": bool(source["top_1_percent_flag"]), "captured_top_5": bool(source["top_5_percent_flag"]),
            "captured_top_10": bool(source["top_10_percent_flag"]), "historical_outcome": int(event), **metadata_columns(),
        })
    return pd.DataFrame(rows)


def build_metadata(bank_count: int, score_rows: int) -> pd.DataFrame:
    entries: tuple[tuple[str, str, str], ...] = (
        ("release_mode", "DEMONSTRATION_ONLY", "release"),
        ("institution_records", "deterministic synthetic examples", "data"),
        ("synthetic_banks", str(bank_count), "data"),
        ("synthetic_bank_quarters", str(score_rows), "data"),
        ("historical_research_bank_quarters", "698804", "research_coverage"),
        ("historical_research_institutions", "11073", "research_coverage"),
        ("historical_research_quarters", "101", "research_coverage"),
        ("locked_test_rows", "113117", "validation"),
        ("locked_test_positive_rows", "58", "validation"),
        ("locked_test_unique_failures", "17", "validation"),
        ("selected_model", FROZEN_MODEL_VERSION, "validation"),
        ("model_interpretation", "relative ranking only", "governance"),
        ("official_camels", "No", "governance"),
        ("calibrated_failure_probability", "No", "governance"),
        ("active_bank_identifiers_in_demo", "No", "privacy"),
        ("raw_fdic_records_in_demo", "No", "redistribution"),
    )
    return pd.DataFrame([
        {"metadata_key": key, "metadata_value": value, "category": category, **metadata_columns()}
        for key, value, category in entries
    ])


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table: pa.Table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd", use_dictionary=True, write_statistics=True)


def write_dictionary(tables: dict[str, pd.DataFrame], path: Path) -> None:
    rows: list[dict[str, str]] = []
    for filename, frame in sorted(tables.items()):
        for column, dtype in frame.dtypes.items():
            rows.append({
                "file": filename,
                "field": str(column),
                "data_type": str(dtype),
                "data_class": "synthetic institution record" if filename != "dashboard_demo_validation.parquet" else "aggregate frozen validation evidence",
                "description": "See dashboard methodology and source schema; no field is an official CAMELS rating or calibrated failure probability.",
            })
    pd.DataFrame(rows).to_csv(path, index=False, lineterminator="\n")


def configuration_digest(bank_count: int) -> str:
    payload: bytes = json.dumps({"bank_count": bank_count, "dates": [str(value.date()) for value in reporting_dates()], "version": DEMO_BUILD_RUN_ID}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_demo_package(root: Path, output_directory: Path, bank_count: int) -> dict[str, object]:
    if bank_count < 100:
        raise ValueError(f"Demo bank count must be at least 100 for usable percentile budgets: bank_count={bank_count}")
    output_directory.mkdir(parents=True, exist_ok=True)
    scores: pd.DataFrame = build_score_rows(bank_count)
    history: pd.DataFrame = build_history(scores)
    peers: pd.DataFrame = build_peer_comparisons(history)
    drivers: pd.DataFrame = build_drivers(history, peers)
    watchlist: pd.DataFrame = build_watchlist(scores, drivers)
    quality: pd.DataFrame = build_quality(scores)
    cases: pd.DataFrame = build_cases(scores)
    validation_source: Path = root / "data/processed/dashboard/model_validation.parquet"
    if not validation_source.exists():
        raise FileNotFoundError(f"Frozen aggregate validation table is required to build the release package: {validation_source}")
    validation: pd.DataFrame = pd.read_parquet(validation_source)
    metadata: pd.DataFrame = build_metadata(bank_count, len(scores))
    sample_columns: list[str] = ["cert", "rssdid", "bank_name", "state", "reporting_date", "asset_size_band", "bank_class", *feature_values(0.5, 1, 1).keys()]
    sample: pd.DataFrame = history.loc[history["reporting_date"] == history["reporting_date"].max(), sample_columns].head(25).copy()
    tables: dict[str, pd.DataFrame] = {
        "synthetic_bank_quarter_sample.parquet": sample,
        "dashboard_demo_scores.parquet": scores,
        "dashboard_demo_history.parquet": history,
        "dashboard_demo_watchlist.parquet": watchlist,
        "dashboard_demo_drivers.parquet": drivers,
        "dashboard_demo_peer_comparisons.parquet": peers,
        "dashboard_demo_validation.parquet": validation,
        "dashboard_demo_case_studies.parquet": cases,
        "dashboard_demo_quality.parquet": quality,
        "dashboard_demo_metadata.parquet": metadata,
    }
    for filename, frame in tables.items():
        write_parquet(frame, output_directory / filename)
    write_dictionary(tables, output_directory / "DATA_DICTIONARY.csv")
    files: list[dict[str, object]] = [
        {"path": filename, "rows": len(frame), "sha256": sha256_file(output_directory / filename), "bytes": (output_directory / filename).stat().st_size}
        for filename, frame in sorted(tables.items())
    ]
    manifest: dict[str, object] = {
        "version": "public-demo-data-v1",
        "build_run_id": DEMO_BUILD_RUN_ID,
        "configuration_hash": configuration_digest(bank_count),
        "deterministic_build_timestamp": DEMO_BUILD_TIMESTAMP,
        "bank_count": bank_count,
        "quarter_count": len(reporting_dates()),
        "data_policy": "Institution-level records are synthetic. The validation table contains frozen aggregate research evidence only.",
        "active_institution_records": False,
        "raw_fdic_records": False,
        "model_binary": False,
        "files": files,
    }
    (output_directory / "SAMPLE_GENERATION_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
