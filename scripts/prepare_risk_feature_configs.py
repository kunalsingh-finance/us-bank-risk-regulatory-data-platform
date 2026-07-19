"""Create frozen, self-hashed Phase 3 feature and peer configurations."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.manifest import JsonObject, configuration_hash, write_replaceable_json  # noqa: E402


def feature(
    name: str,
    category: str,
    numerator: str,
    denominator: str,
    formula: str,
    units: str,
    direction: str,
    minimum_denominator: str,
    annualized: bool,
    source_type: str,
    peer: bool,
    trends: list[str],
    limitation: str,
) -> JsonObject:
    return {
        "feature_name": name,
        "financial_category": category,
        "numerator": numerator,
        "denominator": denominator,
        "formula": formula,
        "units": units,
        "direction_of_risk": direction,
        "minimum_denominator_rule": minimum_denominator,
        "missing_value_rule": "Return null and preserve a feature-quality exception; never impute",
        "availability_period": "2001_Q1 to 2026_Q1 subject to source and history availability",
        "whether_annualized": annualized,
        "whether_source_reported_or_derived": source_type,
        "expected_range": "Feature-specific empirical validation; raw values remain uncapped",
        "warning_range": "Configured broad plausibility or empirical extreme flag",
        "peer_group_requirement": "Quarter-specific final peer group with at least 20 non-null banks" if peer else "None",
        "trend_windows": trends,
        "allowed_downstream_use": "Descriptive risk analysis and later controlled model-candidate review",
        "known_limitation": limitation,
    }


def build_features() -> list[JsonObject]:
    percentage: str = "denominator must be positive and non-null"
    source_ratio: str = "source-reported ratio; no derived denominator"
    rows: list[tuple[str, str, str, str, str, str, str, str, bool, str, bool, list[str], str]] = [
        ("equity_to_assets", "Capital", "equity", "asset", "100 * equity / asset", "percent", "Lower value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q", "8Q"], "Accounting equity is not regulatory capital"),
        ("equity_change_qoq_pct", "Capital", "equity-current minus prior", "absolute prior equity", "100 * change / abs(prior equity)", "percent", "Lower value = higher risk", "absolute prior equity must be positive", False, "Derived", False, ["1Q"], "Percentage change can be unstable near zero equity"),
        ("equity_change_yoy_pct", "Capital", "equity-current minus four-quarter lag", "absolute four-quarter-lag equity", "100 * change / abs(lag equity)", "percent", "Lower value = higher risk", "absolute lag equity must be positive", False, "Derived", True, ["4Q"], "Percentage change can be unstable near zero equity"),
        ("equity_to_assets_change_qoq_pp", "Capital", "current ratio minus prior ratio", "none", "current minus one-quarter lag", "percentage points", "Lower value = higher risk", "not applicable", False, "Derived", False, ["1Q"], "Requires consecutive quarters"),
        ("equity_to_assets_change_yoy_pp", "Capital", "current ratio minus four-quarter lag", "none", "current minus four-quarter lag", "percentage points", "Lower value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Requires exact year-ago quarter"),
        ("equity_to_assets_slope_8q", "Capital", "eight equity-to-assets observations", "quarter index", "REGR_SLOPE over trailing eight quarters", "percentage points per quarter", "Lower value = higher risk", "eight valid observations", False, "Derived", False, ["8Q"], "Short-window linear trend"),
        ("equity_to_assets_volatility_8q", "Capital", "equity_to_assets", "none", "STDDEV_SAMP over trailing eight quarters", "percentage points", "Higher value = higher risk", "eight valid observations", False, "Derived", False, ["8Q"], "Volatility is descriptive, not causality"),
        ("capital_deterioration_flag", "Capital", "capital trend evidence", "none", "1 when equity ratio falls materially", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q", "4Q"], "Screening flag, not an official CAMELS rating"),
        ("past_due_30_89_to_total_loans", "Asset quality", "past_due_30_89", "gross_loans_leases", "100 * numerator / denominator", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Source is past-due assets, used as a loan-denominator proxy"),
        ("past_due_90_plus_to_total_loans", "Asset quality", "past_due_90_plus", "gross_loans_leases", "100 * numerator / denominator", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Source is past-due assets, used as a loan-denominator proxy"),
        ("nonaccrual_assets_to_total_loans", "Asset quality", "nonaccrual_assets", "gross_loans_leases", "100 * numerator / denominator", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Nonaccrual assets are broader than nonaccrual loans"),
        ("noncurrent_assets_to_total_loans", "Asset quality", "past_due_90_plus + nonaccrual_assets", "gross_loans_leases", "100 * numerator / denominator", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q", "8Q"], "Public-data proxy, not FDIC noncurrent-loan ratio"),
        ("net_chargeoffs_to_average_loans", "Asset quality", "quarterly_net_chargeoffs", "average current/prior gross loans", "400 * quarterly flow / average loans", "annualized percent", "Higher value = higher risk", percentage, True, "Derived", True, ["1Q"], "Requires valid prior-quarter balance"),
        ("noncurrent_ratio_change_qoq_pp", "Asset quality", "current noncurrent proxy minus prior", "none", "current minus one-quarter lag", "percentage points", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q"], "Requires consecutive quarters"),
        ("noncurrent_ratio_change_yoy_pp", "Asset quality", "current noncurrent proxy minus year ago", "none", "current minus four-quarter lag", "percentage points", "Higher value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Requires exact year-ago quarter"),
        ("noncurrent_ratio_slope_8q", "Asset quality", "eight noncurrent proxy observations", "quarter index", "REGR_SLOPE over trailing eight quarters", "percentage points per quarter", "Higher value = higher risk", "eight valid observations", False, "Derived", False, ["8Q"], "Short-window linear trend"),
        ("noncurrent_ratio_volatility_8q", "Asset quality", "noncurrent proxy", "none", "STDDEV_SAMP over trailing eight quarters", "percentage points", "Higher value = higher risk", "eight valid observations", False, "Derived", False, ["8Q"], "Proxy volatility"),
        ("asset_quality_deterioration_flag", "Asset quality", "asset-quality change evidence", "none", "1 when noncurrent proxy rises materially", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q", "4Q"], "Screening flag only"),
        ("return_on_assets", "Earnings", "ROAQ", "source-defined average assets", "Direct FDIC quarterly ROA", "annualized percent", "Lower value = higher risk", source_ratio, True, "Source-reported", True, ["1Q", "4Q", "8Q"], "Do not double annualize"),
        ("return_on_equity", "Earnings", "quarterly_net_income", "average current/prior equity", "400 * quarterly income / average equity", "annualized percent", "Lower value = higher risk", percentage, True, "Derived", True, ["1Q"], "Undefined for nonpositive average equity"),
        ("net_interest_margin", "Earnings", "NIMYQ", "source-defined average earning assets", "Direct FDIC quarterly NIM", "annualized percent", "Lower value = higher risk", source_ratio, True, "Source-reported", True, ["1Q", "4Q"], "Rounded source-reported quarterly margin"),
        ("efficiency_ratio", "Earnings", "EEFFQR", "source-defined revenue", "Direct FDIC quarterly efficiency ratio", "percent", "Higher value = higher risk", source_ratio, False, "Source-reported", True, ["1Q", "4Q"], "Extreme values may reflect small denominators"),
        ("net_income_to_average_assets", "Earnings", "quarterly_net_income", "average current/prior assets", "400 * quarterly income / average assets", "annualized percent", "Lower value = higher risk", percentage, True, "Derived", False, ["1Q"], "Requires valid prior-quarter assets"),
        ("net_interest_income_to_average_assets", "Earnings", "quarterly_net_interest_income", "average current/prior assets", "400 * quarterly amount / average assets", "annualized percent", "Lower value = higher risk", percentage, True, "Derived", False, ["1Q"], "Not equivalent to NIM because denominator differs"),
        ("noninterest_expense_to_average_assets", "Earnings", "quarterly_noninterest_expense", "average current/prior assets", "400 * quarterly amount / average assets", "annualized percent", "Higher value = higher risk", percentage, True, "Derived", False, ["1Q"], "Requires valid prior-quarter assets"),
        ("roa_change_qoq_pp", "Earnings", "current ROA minus prior", "none", "current minus one-quarter lag", "percentage points", "Lower value = higher risk", "not applicable", False, "Derived", False, ["1Q"], "Requires consecutive quarters"),
        ("roa_change_yoy_pp", "Earnings", "current ROA minus year ago", "none", "current minus four-quarter lag", "percentage points", "Lower value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Requires exact year-ago quarter"),
        ("roa_mean_8q", "Earnings", "ROA", "none", "AVG over trailing eight quarters", "annualized percent", "Lower value = higher risk", "eight valid observations", True, "Derived", True, ["8Q"], "Backward-looking mean"),
        ("roa_volatility_8q", "Earnings", "ROA", "none", "STDDEV_SAMP over trailing eight quarters", "percentage points", "Higher value = higher risk", "eight valid observations", False, "Derived", True, ["8Q"], "Backward-looking volatility"),
        ("consecutive_loss_quarters", "Earnings", "negative quarterly net income sequence", "none", "running count since last non-loss quarter", "quarters", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q"], "Null income resets no evidence and is flagged"),
        ("earnings_deterioration_flag", "Earnings", "earnings trend evidence", "none", "1 when ROA deteriorates or losses persist", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q", "4Q"], "Screening flag only"),
        ("liquid_assets_to_total_assets", "Liquidity", "cash_balances + securities + fed_funds_reverse_repos", "asset", "100 * proxy liquid assets / assets", "percent", "Lower value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Broad proxy; securities liquidity varies"),
        ("loans_to_deposits", "Liquidity", "gross_loans_leases", "deposits", "100 * loans / deposits", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Does not capture all funding sources"),
        ("deposits_to_total_assets", "Funding", "deposits", "asset", "100 * deposits / assets", "percent", "Lower value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Deposit composition unavailable in Core-v1"),
        ("assessable_deposits_to_total_deposits", "Funding", "assessable_deposits", "deposits", "100 * assessable deposits / deposits", "percent", "Descriptive only", percentage, False, "Derived", False, ["1Q"], "Not brokered or uninsured deposits"),
        ("fhlb_advances_to_total_assets", "Funding", "fhlb_advances", "asset", "100 * advances / assets", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Only FHLB advances, not all wholesale funding"),
        ("deposit_growth_qoq_pct", "Funding", "deposits-current minus prior", "absolute prior deposits", "100 * change / abs(prior deposits)", "percent", "Non-monotonic", "absolute prior deposits must be positive", False, "Derived", False, ["1Q"], "Rapid decline or growth can both warrant review"),
        ("deposit_growth_yoy_pct", "Funding", "deposits-current minus year ago", "absolute year-ago deposits", "100 * change / abs(year-ago deposits)", "percent", "Non-monotonic", "absolute lag deposits must be positive", False, "Derived", True, ["4Q"], "Rapid decline or growth can both warrant review"),
        ("estimated_deposit_outflow_pct", "Funding", "positive decline from prior deposits", "prior deposits", "100 * max(prior-current,0) / prior", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q"], "Accounting change proxy, not observed cash outflow"),
        ("funding_cost", "Funding", "INTEXPYQ", "source-defined earning assets", "Direct FDIC quarterly funding cost", "annualized percent", "Higher value = higher risk", source_ratio, True, "Source-reported", True, ["1Q", "4Q"], "Do not double annualize"),
        ("funding_cost_change_qoq_pp", "Funding", "current funding cost minus prior", "none", "current minus one-quarter lag", "percentage points", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q"], "Requires consecutive quarters"),
        ("funding_cost_change_yoy_pp", "Funding", "current funding cost minus year ago", "none", "current minus four-quarter lag", "percentage points", "Higher value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Requires exact year-ago quarter"),
        ("liquidity_deterioration_flag", "Liquidity", "liquidity trend evidence", "none", "1 when liquid share falls or loan/deposit pressure is high", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q"], "Screening flag only"),
        ("funding_pressure_flag", "Funding", "funding trend evidence", "none", "1 when outflow, cost, or FHLB reliance is elevated", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q", "4Q"], "Screening flag only"),
        ("reported_real_estate_loans_to_total_loans", "Concentration", "construction + multifamily + residential", "gross loans", "100 * categories / gross loans", "percent", "Non-monotonic", percentage, False, "Derived", False, ["1Q", "4Q"], "Reported categories are an incomplete CRE/business-model proxy"),
        ("construction_to_total_loans", "Concentration", "construction_loans", "gross loans", "100 * category / gross loans", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Concentration does not imply loss"),
        ("multifamily_to_total_loans", "Concentration", "multifamily_loans", "gross loans", "100 * category / gross loans", "percent", "Non-monotonic", percentage, False, "Derived", True, ["1Q", "4Q"], "Business-model descriptor"),
        ("residential_mortgages_to_total_loans", "Concentration", "residential_loans", "gross loans", "100 * category / gross loans", "percent", "Non-monotonic", percentage, False, "Derived", False, ["1Q"], "Business-model descriptor"),
        ("commercial_industrial_to_total_loans", "Concentration", "commercial_industrial_loans", "gross loans", "100 * category / gross loans", "percent", "Non-monotonic", percentage, False, "Derived", False, ["1Q"], "Business-model descriptor"),
        ("consumer_to_total_loans", "Concentration", "consumer loans excluding credit cards", "gross loans", "100 * max(consumer-credit cards,0) / gross loans", "percent", "Non-monotonic", percentage, False, "Derived", False, ["1Q"], "Assumes credit cards are nested within consumer loans"),
        ("credit_card_to_total_loans", "Concentration", "credit_card_loans", "gross loans", "100 * category / gross loans", "percent", "Non-monotonic", percentage, False, "Derived", False, ["1Q"], "Business-model descriptor"),
        ("largest_reported_loan_category_share", "Concentration", "largest non-overlapping reported category", "gross loans", "100 * max category / gross loans", "percent", "Higher value = higher risk", percentage, False, "Derived", True, ["1Q", "4Q"], "Only six reported categories"),
        ("loan_concentration_hhi", "Concentration", "sum of squared reported category shares", "covered category balances", "sum((category/covered total)^2)", "0-to-1 index", "Higher value = higher risk", "covered category total must be positive", False, "Derived", True, ["1Q", "4Q"], "Incomplete portfolio HHI; categories documented and coverage retained"),
        ("loan_category_coverage_ratio", "Concentration", "non-overlapping reported categories", "gross loans", "100 * covered categories / gross loans", "percent", "Descriptive only", percentage, False, "Derived", False, ["1Q"], "Coverage may exceed expectations if source categories overlap or definitions shift"),
        ("concentration_change_yoy", "Concentration", "current HHI minus year-ago HHI", "none", "current minus four-quarter lag", "index change", "Higher value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Requires comparable category coverage"),
        ("concentration_pressure_flag", "Concentration", "HHI and coverage evidence", "none", "1 when HHI is high with adequate coverage", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["1Q", "4Q"], "Screening flag only"),
        ("total_asset_growth_qoq_pct", "Growth", "assets-current minus prior", "absolute prior assets", "100 * change / abs(prior assets)", "percent", "Higher value = higher risk", "absolute prior assets must be positive", False, "Derived", False, ["1Q"], "Growth may be merger-driven"),
        ("total_asset_growth_yoy_pct", "Growth", "assets-current minus year ago", "absolute year-ago assets", "100 * change / abs(year-ago assets)", "percent", "Higher value = higher risk", "absolute lag assets must be positive", False, "Derived", True, ["4Q"], "Growth may be merger-driven"),
        ("total_loan_growth_qoq_pct", "Growth", "loans-current minus prior", "absolute prior loans", "100 * change / abs(prior loans)", "percent", "Higher value = higher risk", "absolute prior loans must be positive", False, "Derived", False, ["1Q"], "Growth may reflect portfolio transfers"),
        ("total_loan_growth_yoy_pct", "Growth", "loans-current minus year ago", "absolute year-ago loans", "100 * change / abs(year-ago loans)", "percent", "Higher value = higher risk", "absolute lag loans must be positive", False, "Derived", True, ["4Q"], "Growth may reflect portfolio transfers"),
        ("equity_growth_yoy_pct", "Growth", "equity-current minus year ago", "absolute year-ago equity", "100 * change / abs(year-ago equity)", "percent", "Lower value = higher risk", "absolute lag equity must be positive", False, "Derived", False, ["4Q"], "Unstable near zero equity"),
        ("loan_growth_minus_deposit_growth", "Growth", "loan growth minus deposit growth", "none", "year-over-year loan growth minus deposit growth", "percentage points", "Higher value = higher risk", "both component growth rates required", False, "Derived", True, ["4Q"], "Relative growth pressure proxy"),
        ("rapid_asset_growth_flag", "Growth", "asset growth", "none", "1 when year-over-year asset growth exceeds 25%", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Threshold is a screening rule"),
        ("rapid_loan_growth_flag", "Growth", "loan growth", "none", "1 when year-over-year loan growth exceeds 25%", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Threshold is a screening rule"),
        ("funding_gap_flag", "Growth", "loan versus deposit growth", "none", "1 when loan growth exceeds deposit growth by 15 points", "flag", "Higher value = higher risk", "not applicable", False, "Derived", False, ["4Q"], "Screening rule, not liquidity forecast"),
    ]
    return [feature(*row) for row in rows]


def hashed_config(payload: JsonObject) -> JsonObject:
    payload["configuration_hash"] = configuration_hash(payload)
    return payload


def main() -> None:
    features: list[JsonObject] = build_features()
    risk: JsonObject = hashed_config({
        "version": "phase3-risk-features-v1",
        "run_id": "phase3-20260716t230347z",
        "build_timestamp": "2026-07-16T23:03:47Z",
        "input_database": "database/bank_risk.duckdb",
        "input_database_sha256": "678d07fcd1c82d5737f44ebd40b57e7d09da4479a62ca6e8150ece55300f2246",
        "input_configuration_hash": "d5530cfc0cbba22cc0f729fd1fa52834f16f687c3fcd6d7f041c137ab1cc3286",
        "output_database": "database/bank_risk_features.duckdb",
        "expected_rows": 698804,
        "features": features,
        "unsupported_candidates": [
            "tier1_leverage_ratio", "tier1_risk_based_capital_ratio", "total_risk_based_capital_ratio",
            "regulatory_capital_buffer", "allowance_to_total_loans", "allowance_to_noncurrent_loans",
            "provisions_to_average_assets", "provision_burden", "brokered_deposits_to_total_deposits",
            "uninsured_deposits_to_total_deposits", "short_term_borrowings_to_total_assets",
            "other_borrowed_funds_to_total_assets", "agricultural_loans_to_total_loans",
        ],
        "sql_execution_order": [f"sql/phase3/{number:03d}_{name}.sql" for number, name in enumerate([
            "create_feature_tables", "build_base_financial_measures", "build_capital_features",
            "build_asset_quality_features", "build_earnings_features", "build_liquidity_funding_features",
            "build_concentration_features", "build_growth_features", "build_temporal_features",
            "build_peer_groups", "build_peer_benchmarks", "build_feature_quality_flags",
            "run_feature_controls", "create_reporting_views", "build_report_views",
        ], start=1)],
    })
    peers: JsonObject = hashed_config({
        "version": "phase3-peer-groups-v1",
        "asset_units": "USD thousands",
        "minimum_standard_peer_count": 20,
        "fallback": "Drop bank class and use same-quarter asset-size band",
        "asset_bands": [
            {"label": "LT_100M", "lower_inclusive": 0, "upper_exclusive": 100000},
            {"label": "100M_500M", "lower_inclusive": 100000, "upper_exclusive": 500000},
            {"label": "500M_1B", "lower_inclusive": 500000, "upper_exclusive": 1000000},
            {"label": "1B_10B", "lower_inclusive": 1000000, "upper_exclusive": 10000000},
            {"label": "10B_50B", "lower_inclusive": 10000000, "upper_exclusive": 50000000},
            {"label": "50B_250B", "lower_inclusive": 50000000, "upper_exclusive": 250000000},
            {"label": "GE_250B", "lower_inclusive": 250000000, "upper_exclusive": None},
        ],
        "peer_features": [item["feature_name"] for item in features if item["peer_group_requirement"] != "None"],
    })
    quality: JsonObject = hashed_config({
        "version": "phase3-feature-quality-v1",
        "minimum_rolling_observations": 8,
        "minimum_peer_count": 20,
        "extreme_absolute_percentage": 1000,
        "growth_warning_percent": 25,
        "funding_gap_warning_points": 15,
        "rules": [
            "missing_numerator", "missing_denominator", "zero_denominator", "negative_denominator",
            "insufficient_lag_history", "insufficient_rolling_history", "conditional_field_unavailable",
            "peer_group_too_small", "extreme_preserved_value", "suspected_unit_issue",
            "identifier_continuity_concern", "source_field_quality_warning",
        ],
    })
    outputs: tuple[tuple[Path, JsonObject], ...] = (
        (ROOT / "configs/risk_features.yaml", risk),
        (ROOT / "configs/peer_groups.yaml", peers),
        (ROOT / "configs/feature_quality_rules.yaml", quality),
    )
    for path, payload in outputs:
        digest: str = write_replaceable_json(path, payload)
        print(f"{path.relative_to(ROOT)} file_sha256={digest} configuration_hash={payload['configuration_hash']}")


if __name__ == "__main__":
    main()
