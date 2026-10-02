"""Streamlit page renderers backed only by prepared Parquet tables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import streamlit as st

from .charts import category_alerts, feature_history, lead_time_histogram, peer_box, percentile_history, tier_distribution, validation_curve
from .config import load_dashboard_configs
from .data_access import distinct_values, latest_reporting_date, parquet_columns, parquet_sql, query_parquet
from .formatting import ASSET_BAND_LABELS, feature_label, percentile_label
from .rankings import current_review_population


ROOT: Path = Path(__file__).resolve().parents[2]
DATA: Path = Path(os.environ["BANK_RISK_DASHBOARD_DATA_DIR"]).resolve() if "BANK_RISK_DASHBOARD_DATA_DIR" in os.environ else ROOT / "data/processed/dashboard"
DEMO_MODE: bool = os.environ.get("BANK_RISK_DEMO_MODE", "0") == "1"
DEMO_TABLE_NAMES: dict[str, str] = {
    "bank_scores": "dashboard_demo_scores.parquet",
    "bank_history": "dashboard_demo_history.parquet",
    "current_watchlist": "dashboard_demo_watchlist.parquet",
    "driver_explanations": "dashboard_demo_drivers.parquet",
    "peer_comparisons": "dashboard_demo_peer_comparisons.parquet",
    "model_validation": "dashboard_demo_validation.parquet",
    "failure_case_studies": "dashboard_demo_case_studies.parquet",
    "data_quality": "dashboard_demo_quality.parquet",
    "metadata": "dashboard_demo_metadata.parquet",
}


def dashboard_table_path(name: str) -> Path:
    filename: str = DEMO_TABLE_NAMES[name] if DEMO_MODE else f"{name}.parquet"
    return DATA / filename


@st.cache_data(show_spinner=False)
def cached_query(name: str, columns: tuple[str, ...], where_sql: str, parameters: tuple[object, ...]) -> pd.DataFrame:
    return query_parquet(dashboard_table_path(name), columns, where_sql, parameters)


@st.cache_data(show_spinner=False)
def cached_distinct(name: str, column: str) -> list[object]:
    return distinct_values(dashboard_table_path(name), column)


@st.cache_data(show_spinner=False)
def cached_table(name: str) -> pd.DataFrame:
    path: Path = dashboard_table_path(name)
    return query_parquet(path, parquet_columns(path), "", tuple())


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, page_icon="🏦", layout="wide")
    st.markdown("""<style>
        .block-container {padding-top: 1.5rem; max-width: 1500px;}
        section[data-testid="stSidebar"] {width:18rem !important;min-width:18rem !important;max-width:18rem !important;}
        h1 {font-size:2rem !important;line-height:1.12 !important;white-space:normal;overflow-wrap:anywhere;}
        [data-testid="stMetric"] {background:#F4F7F9;border:1px solid #D9E2E8;border-radius:8px;padding:12px;color:#14213D;}
        [data-testid="stMetric"] * {color:#14213D;}
        .risk-note {background:#FFF7E6;border-left:5px solid #E09F3E;padding:12px;border-radius:4px;color:#14213D;}
        .governance-note {background:#EDF5F7;border-left:5px solid #177E89;padding:12px;border-radius:4px;color:#14213D;}
    </style>""", unsafe_allow_html=True)


def persistent_header(title: str, subtitle: str) -> None:
    _, _, _, disclaimers = load_dashboard_configs(ROOT)
    st.title(title)
    st.caption(subtitle)
    if DEMO_MODE:
        st.info("DEMONSTRATION MODE — institution records are deterministic synthetic examples. They do not represent actual banks or current monitoring results. A ranking is not a probability. Frozen validation statistics are aggregate historical research results.")
    st.markdown(f"<div class='governance-note'>{disclaimers['persistent']}</div>", unsafe_allow_html=True)


def reporting_dates() -> list[pd.Timestamp]:
    return [pd.Timestamp(value) for value in reversed(cached_distinct("bank_scores", "reporting_date"))]


def render_executive() -> None:
    configure_page("Bank Risk | Executive Overview")
    persistent_header("U.S. Bank Risk Early-Warning Platform", "Executive overview · public-data relative ranking")
    dates: list[pd.Timestamp] = reporting_dates()
    selected: pd.Timestamp = st.selectbox("Reporting quarter", dates, format_func=lambda value: value.strftime("%Y Q") + str(value.quarter))
    columns: tuple[str, ...] = ("cert", "reporting_date", "asset_size_band", "bank_class", "risk_tier", "top_1_percent_flag", "top_5_percent_flag", "top_10_percent_flag", "feature_quality_status", "frozen_model_version", "prediction_split")
    frame: pd.DataFrame = cached_query("bank_scores", columns, "reporting_date=?", (selected,))
    prior: pd.Timestamp = selected - pd.offsets.QuarterEnd()
    prior_count: int = len(cached_query("bank_scores", ("cert",), "reporting_date=? AND top_5_percent_flag", (prior,)))
    metrics_primary = st.columns(3)
    metrics_primary[0].metric("Eligible institutions", f"{len(frame):,}")
    metrics_primary[1].metric("Top 1%", f"{int(frame['top_1_percent_flag'].sum()):,}")
    metrics_primary[2].metric("Top 5%", f"{int(frame['top_5_percent_flag'].sum()):,}", delta=f"{int(frame['top_5_percent_flag'].sum())-prior_count:+,} vs prior quarter")
    metrics_secondary = st.columns(2)
    metrics_secondary[0].metric("Top 10%", f"{int(frame['top_10_percent_flag'].sum()):,}")
    metrics_secondary[1].metric("Quality warnings", f"{int((frame['feature_quality_status']!='PASS').sum()):,}")
    left, right = st.columns(2)
    left.plotly_chart(tier_distribution(frame), width="stretch")
    right.plotly_chart(category_alerts(frame.loc[frame["top_10_percent_flag"]], "asset_size_band", "Top-10% indicators by asset band"), width="stretch")
    left2, right2 = st.columns(2)
    left2.plotly_chart(category_alerts(frame.loc[frame["top_10_percent_flag"]], "bank_class", "Top-10% indicators by bank class"), width="stretch")
    right2.markdown("### Governance snapshot")
    right2.write(f"Model: `{frame['frozen_model_version'].iloc[0]}`")
    right2.write(f"Prediction split: **{frame['prediction_split'].iloc[0]}**")
    right2.markdown("<div class='risk-note'><b>Major limitations:</b> only 17 unique failures support the locked test; calibration was weak; results varied by year and asset band; false alerts are expected.</div>", unsafe_allow_html=True)


def render_watchlist() -> None:
    configure_page("Bank Risk | Current Watchlist")
    persistent_header("Current Monitoring Watchlist", "Latest prepared quarter · selectable review budget")
    latest = latest_reporting_date(dashboard_table_path("bank_scores"))
    scores = cached_query("bank_scores", parquet_columns(dashboard_table_path("bank_scores")), "reporting_date=?", (latest,))
    drivers = cached_query("driver_explanations", ("cert", "reporting_date", "driver_rank", "feature_name"), "reporting_date=?", (latest,))
    frame: pd.DataFrame = current_review_population(scores, drivers)
    states: list[str] = sorted(frame["state"].dropna().unique().tolist())
    bands: list[str] = sorted(frame["asset_size_band"].dropna().unique().tolist())
    classes: list[str] = sorted(frame["bank_class"].dropna().unique().tolist())
    tiers: list[str] = sorted(frame["risk_tier"].dropna().unique().tolist())
    filters = st.columns(4)
    selected_states: list[str] = filters[0].multiselect("State", states)
    selected_bands: list[str] = filters[1].multiselect("Asset-size band", bands, format_func=lambda value: ASSET_BAND_LABELS.get(value, value))
    selected_classes: list[str] = filters[2].multiselect("Bank class", classes)
    selected_tiers: list[str] = filters[3].multiselect("Risk tier", tiers)
    top_filter: str = st.radio("Monitoring subset", ["Top 5%", "Top 1%", "Top 10%"], horizontal=True)
    filtered: pd.DataFrame = frame.copy()
    for column, values in (("state", selected_states), ("asset_size_band", selected_bands), ("bank_class", selected_classes), ("risk_tier", selected_tiers)):
        if values:
            filtered = filtered.loc[filtered[column].isin(values)]
    budget_flag = {"Top 1%": "top_1_percent_flag", "Top 5%": "top_5_percent_flag", "Top 10%": "top_10_percent_flag"}[top_filter]
    filtered = filtered.loc[filtered[budget_flag]]
    display: pd.DataFrame = filtered[["bank_name", "cert", "state", "asset_size_band", "bank_class", "same_quarter_percentile", "same_quarter_rank", "risk_tier", "percentile_change_qoq", "percentile_change_yoy", "top_driver_1", "top_driver_2", "top_driver_3", "data_quality_warning", "prediction_split"]].copy()
    display = display.rename(columns={"bank_name": "Bank", "cert": "CERT", "same_quarter_percentile": "Percentile", "same_quarter_rank": "Rank"})
    st.dataframe(display, width="stretch", hide_index=True, column_config={"Percentile": st.column_config.NumberColumn(format="%.1f")})


@st.cache_data(show_spinner=False)
def bank_options() -> pd.DataFrame:
    connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
    try:
        return connection.execute(f"SELECT cert,MAX(bank_name) bank_name FROM read_parquet('{parquet_sql(dashboard_table_path('bank_scores'))}') GROUP BY cert ORDER BY bank_name,cert").fetch_df()
    finally:
        connection.close()


def render_bank_detail() -> None:
    configure_page("Bank Risk | Bank Detail")
    persistent_header("Bank Detail", "Relative ranking, feature history, peers, and associated drivers")
    _, _, _, disclaimers = load_dashboard_configs(ROOT)
    options: pd.DataFrame = bank_options()
    labels: list[str] = [f"{row.bank_name} · CERT {row.cert}" for row in options.itertuples()]
    selected_label: str = st.selectbox("Search bank name or CERT", labels)
    cert: int = int(options.iloc[labels.index(selected_label)]["cert"])
    history_columns: tuple[str, ...] = parquet_columns(dashboard_table_path("bank_history"))
    history: pd.DataFrame = cached_query("bank_history", history_columns, "cert=?", (cert,)).sort_values("reporting_date")
    if history.empty:
        st.warning("No prepared history is available for this institution.")
        return
    dates: list[pd.Timestamp] = [pd.Timestamp(value) for value in reversed(history["reporting_date"].tolist())]
    selected_date: pd.Timestamp = st.selectbox("Reporting quarter", dates, format_func=lambda value: f"{value.year} Q{value.quarter}")
    current: pd.Series = history.loc[pd.to_datetime(history["reporting_date"]) == selected_date].iloc[0]
    metrics_primary = st.columns(2)
    metrics_primary[0].metric("Same-quarter percentile", percentile_label(float(current["same_quarter_percentile"])))
    metrics_primary[1].metric("Rank", f"{int(current['same_quarter_rank']):,} of {int(current['scored_population']):,}")
    metrics_secondary = st.columns(2)
    metrics_secondary[0].metric("Risk tier", str(current["risk_tier"]))
    metrics_secondary[1].metric("Monitoring", "Top 5%" if bool(current["top_5_percent_flag"]) else "Outside top 5%")
    st.markdown(f"<div class='risk-note'>{disclaimers['bank_detail']}</div>", unsafe_allow_html=True)
    st.plotly_chart(percentile_history(history.tail(8)), width="stretch")
    feature_groups: dict[str, tuple[str, ...]] = {
        "Capital": ("equity_to_assets", "equity_change_yoy_pct"),
        "Asset quality": ("noncurrent_assets_to_total_loans", "past_due_30_89_to_total_loans"),
        "Earnings": ("return_on_assets", "return_on_equity", "net_interest_margin"),
        "Liquidity and funding": ("liquid_assets_to_total_assets", "loans_to_deposits", "funding_cost"),
        "Growth and concentration": ("total_asset_growth_yoy_pct", "total_loan_growth_yoy_pct", "loan_concentration_hhi"),
    }
    tabs = st.tabs(list(feature_groups))
    for tab, (_, features) in zip(tabs, feature_groups.items(), strict=True):
        columns = tab.columns(len(features))
        for column, feature in zip(columns, features, strict=True):
            column.plotly_chart(feature_history(history.tail(8), feature, feature_label(feature)), width="stretch")
    driver_columns: tuple[str, ...] = parquet_columns(dashboard_table_path("driver_explanations"))
    drivers: pd.DataFrame = cached_query("driver_explanations", driver_columns, "cert=? AND reporting_date=?", (cert, selected_date))
    st.subheader(str(disclaimers["driver_heading"]))
    if drivers.empty:
        st.info("No linked driver explanation is available for this bank-quarter.")
    else:
        st.dataframe(drivers[["driver_rank", "feature_name", "driver_direction", "current_feature_value", "peer_median", "bank_percentile", "peer_comparison_warning"]], width="stretch", hide_index=True)
    if str(current["feature_quality_status"]) != "PASS" or str(current["peer_benchmark_status"]) != "PASS":
        st.warning(f"Feature quality: {current['feature_quality_status']} · Peer benchmark: {current['peer_benchmark_status']}")


def render_peer_comparison() -> None:
    configure_page("Bank Risk | Peer Comparison")
    persistent_header("Same-Quarter Peer Comparison", "Quarter-specific asset-band and bank-class benchmarks")
    options: pd.DataFrame = bank_options()
    labels: list[str] = [f"{row.bank_name} · CERT {row.cert}" for row in options.itertuples()]
    selected: str = st.selectbox("Institution", labels)
    cert: int = int(options.iloc[labels.index(selected)]["cert"])
    dates: list[pd.Timestamp] = [pd.Timestamp(value) for value in reversed(cached_distinct("peer_comparisons", "reporting_date"))]
    date: pd.Timestamp = st.selectbox("Reporting quarter", dates, format_func=lambda value: f"{value.year} Q{value.quarter}")
    columns: tuple[str, ...] = parquet_columns(dashboard_table_path("peer_comparisons"))
    peers: pd.DataFrame = cached_query("peer_comparisons", columns, "cert=? AND reporting_date=?", (cert, date))
    if peers.empty:
        st.info("No prepared same-quarter peer comparison is available for this selection.")
        return
    feature: str = st.selectbox("Feature", peers["feature_name"].tolist(), format_func=feature_label)
    row: pd.DataFrame = peers.loc[peers["feature_name"] == feature]
    metrics_primary = st.columns(2)
    metrics_primary[0].metric("Peer group size", f"{int(row.iloc[0]['peer_count']):,}")
    metrics_primary[1].metric("Institution value", f"{float(row.iloc[0]['feature_value']):.2f}")
    metrics_secondary = st.columns(2)
    metrics_secondary[0].metric("Peer median", f"{float(row.iloc[0]['peer_median']):.2f}")
    metrics_secondary[1].metric("Difference from median", f"{float(row.iloc[0]['difference_from_peer_median']):+.2f}")
    st.write(f"Peer definition: `{row.iloc[0]['final_peer_group_id']}` · Method: **{row.iloc[0]['peer_group_method']}**")
    st.plotly_chart(peer_box(row, feature_label(feature)), width="stretch")
    if bool(row.iloc[0]["peer_feature_count_too_small"]):
        st.warning("Peer feature group contains fewer than 20 non-null observations.")


def render_model_validation() -> None:
    configure_page("Bank Risk | Model Validation")
    persistent_header("Frozen Model Validation", "Historical out-of-sample results · no post-test tuning")
    frame: pd.DataFrame = cached_table("model_validation")
    headline: dict[str, float] = {str(row.metric_name): float(row.y_value) for row in frame.loc[frame["section"] == "headline"].itertuples()}
    metrics_primary = st.columns(3)
    metrics_primary[0].metric("PR-AUC", f"{headline['average_precision']:.6f}")
    metrics_primary[1].metric("No-skill PR-AUC", f"{headline['baseline_average_precision']:.6f}")
    metrics_primary[2].metric("PR-AUC lift", f"{headline['pr_auc_lift']:.1f}×")
    metrics_secondary = st.columns(2)
    metrics_secondary[0].metric("ROC AUC", f"{headline['roc_auc']:.6f}")
    metrics_secondary[1].metric("Calibration slope", f"{headline['calibration_slope']:.3f}")
    st.error("Only 17 unique failures occurred in the locked test. Calibration was weak, and performance varied materially by year and asset band. The system is approved for relative ranking, not individual-bank likelihood estimation.")
    left, right = st.columns(2)
    left.plotly_chart(validation_curve(frame, "precision_recall_curve", "Precision-recall curve", "Recall", "Precision"), width="stretch")
    right.plotly_chart(validation_curve(frame, "roc_curve", "ROC curve", "False-positive rate", "True-positive rate"), width="stretch")
    left2, right2 = st.columns(2)
    left2.plotly_chart(validation_curve(frame, "calibration", "Calibration diagnostic", "Mean score", "Observed event rate"), width="stretch")
    right2.plotly_chart(lead_time_histogram(frame), width="stretch")
    st.markdown("### Frozen alert-budget results")
    alerts: pd.DataFrame = frame.loc[frame["section"] == "alert_budget", ["series", "metric_name", "y_value"]].pivot(index="series", columns="metric_name", values="y_value").reset_index()
    st.dataframe(alerts[["series", "alerts", "false_alerts", "precision", "recall"]], width="stretch", hide_index=True)
    st.markdown(
        f"**Unique failures captured:** top 1% = {int(headline['captured_failures_top_1'])}/{int(headline['unique_locked_test_failures'])} · "
        f"top 5% = {int(headline['captured_failures_top_5'])}/{int(headline['unique_locked_test_failures'])} · "
        f"top 10% = {int(headline['captured_failures_top_10'])}/{int(headline['unique_locked_test_failures'])}. "
        f"Median top-5% lead time = {int(headline['median_top_5_lead_days'])} days. "
        f"Locked-test access count = {int(headline['locked_test_access_count'])}."
    )
    st.markdown("### Institution-bootstrap 95% uncertainty intervals")
    uncertainty: pd.DataFrame = frame.loc[frame["section"] == "uncertainty_interval", ["series", "metric_name", "y_value"]].pivot(index="series", columns="metric_name", values="y_value").reset_index()
    st.dataframe(uncertainty[["series", "lower_95", "median", "upper_95"]], width="stretch", hide_index=True)
    st.markdown("### Performance by year")
    period: pd.DataFrame = frame.loc[frame["section"] == "performance_by_year", ["series", "metric_name", "y_value", "detail"]].pivot(index=["series", "detail"], columns="metric_name", values="y_value").reset_index()
    st.dataframe(period.rename(columns={"series": "reporting_year", "detail": "reliability"}), width="stretch", hide_index=True)
    st.markdown("### Performance by asset band")
    bands: pd.DataFrame = frame.loc[frame["section"] == "performance_by_asset_band", ["series", "metric_name", "y_value", "detail"]].pivot(index=["series", "detail"], columns="metric_name", values="y_value").reset_index()
    st.dataframe(bands.rename(columns={"series": "asset_size_band", "detail": "reliability"}), width="stretch", hide_index=True)


def render_case_studies() -> None:
    configure_page("Bank Risk | Failure Case Studies")
    title: str = "Synthetic Demonstration Case Studies" if DEMO_MODE else "Historical Failure Case Studies"
    subtitle: str = "Illustrative synthetic captured, missed, and false-alert scenarios" if DEMO_MODE else "Frozen balanced selection of captured, missed, and false-positive examples"
    persistent_header(title, subtitle)
    cases: pd.DataFrame = cached_table("failure_case_studies")
    roles: list[str] = cases["case_role"].tolist()
    role: str = st.selectbox("Case role", roles)
    row: pd.Series = cases.loc[cases["case_role"] == role].iloc[0]
    if row["selection_status"] != "SELECTED":
        st.info(str(row["selection_rationale"]))
        return
    st.subheader(f"{row['bank_name']} · CERT {int(row['cert'])}")
    st.write(str(row["selection_rationale"]))
    metrics_primary = st.columns(2)
    metrics_primary[0].metric("Reporting quarter", pd.Timestamp(row["reporting_date"]).strftime("%Y Q") + str(pd.Timestamp(row["reporting_date"]).quarter))
    metrics_primary[1].metric("Same-quarter percentile", f"{float(row['same_quarter_percentile']):.1f}")
    metrics_secondary = st.columns(2)
    metrics_secondary[0].metric("Failure date", str(row["failure_date"])[:10] if pd.notna(row["failure_date"]) else "No observed event")
    metrics_secondary[1].metric("Top-5% lead days", f"{int(row['lead_days_top_5'])}" if pd.notna(row["lead_days_top_5"]) else "Not captured")
    st.write(f"Captured at top 1%: **{bool(row['captured_top_1'])}** · top 5%: **{bool(row['captured_top_5'])}** · top 10%: **{bool(row['captured_top_10'])}**")
    history_columns: tuple[str, ...] = parquet_columns(dashboard_table_path("bank_history"))
    history: pd.DataFrame = cached_query("bank_history", history_columns, "cert=?", (int(row["cert"]),)).sort_values("reporting_date")
    st.plotly_chart(percentile_history(history.tail(8)), width="stretch")


def render_data_quality() -> None:
    configure_page("Bank Risk | Data Quality and Lineage")
    persistent_header("Data Quality and Lineage", "Coverage, warnings, hashes, and build provenance")
    metadata: pd.DataFrame = cached_table("metadata")
    scores_date: pd.Timestamp = latest_reporting_date(dashboard_table_path("bank_scores"))
    quality_columns: tuple[str, ...] = parquet_columns(dashboard_table_path("data_quality"))
    quality: pd.DataFrame = cached_query("data_quality", quality_columns, "reporting_date=?", (scores_date,))
    metrics_primary = st.columns(2)
    metrics_primary[0].metric("Canonical bank-quarters", "698,804")
    metrics_primary[1].metric("Historical institutions", "11,073")
    metrics_secondary = st.columns(2)
    metrics_secondary[0].metric("Historical quarters", "101")
    metrics_secondary[1].metric("Latest score quarter", f"{scores_date.year} Q{scores_date.quarter}")
    if DEMO_MODE:
        st.caption("The historical coverage counts describe the governed research build. Institution-level tables shown in demonstration mode are synthetic.")
    st.markdown("### Latest-quarter warning profile")
    warning_summary: pd.DataFrame = quality.groupby(["feature_quality_status", "peer_benchmark_status"], as_index=False).agg(observations=("cert", "size"))
    st.dataframe(warning_summary, width="stretch", hide_index=True)
    st.markdown("### Build and configuration lineage")
    st.dataframe(metadata[["category", "metadata_key", "metadata_value"]], width="stretch", hide_index=True)
    unavailable_cases: pd.DataFrame = cached_table("failure_case_studies").loc[lambda value: value["selection_status"] != "SELECTED", ["case_role", "selection_status", "selection_rationale"]]
    st.markdown("### Open dashboard exceptions")
    if unavailable_cases.empty:
        st.success("No open presentation-layer case-selection exceptions.")
    else:
        st.dataframe(unavailable_cases, width="stretch", hide_index=True)


def render_methodology() -> None:
    configure_page("Bank Risk | Methodology and Limitations")
    persistent_header("Methodology and Limitations", "How to interpret this public-data monitoring demonstration")
    st.markdown("""
### Public-data framework

The platform uses FDIC institution and quarterly financial data to construct public-data CAMELS-style risk indicators. Actual supervisory CAMELS information is confidential and is not used.

### Outcome and exclusions

The primary research outcome is FDIC failure within four quarters. Assistance transactions, mergers, acquisitions, charter changes, and ordinary exits are kept separate. Censored observations are not treated as confirmed negatives.

### Chronological validation

Models were developed with expanding-window validation. Training-only preprocessing, a frozen validation selection, and one locked-test access control future leakage. The dashboard reads prepared presentation tables and does not retrain or rescore the model.

### Material limitations

- The locked test contains only 17 unique failing banks.
- Calibration was weak, so scores are shown as same-quarter rankings and tiers.
- Performance varied materially across time and asset bands.
- Same-quarter peers can be small or have missing features.
- Public regulatory data cannot reproduce confidential supervisory information.
- Feature importance and local perturbations are associative, not causal.
- The platform provides no regulatory or investment advice and makes no guaranteed institution-level prediction.
""")
