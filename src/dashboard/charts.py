"""Consistent Plotly charts for the Phase 6 dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLORS: dict[str, str] = {
    "navy": "#12314A", "teal": "#177E89", "blue": "#2E6F95", "amber": "#E09F3E",
    "red": "#C44536", "gray": "#667085", "light": "#E8EEF2",
}
TIER_COLORS: dict[str, str] = {
    "Low": "#4F8A6F", "Moderate": "#6B8E9B", "Elevated": "#E0A43A",
    "High": "#D46A3A", "Highest monitored tier": "#A63D40",
}


def finance_layout(figure: go.Figure, title: str) -> go.Figure:
    figure.update_layout(title=title, template="plotly_white", font={"family": "Arial", "color": COLORS["navy"]},
                         margin={"l": 30, "r": 20, "t": 60, "b": 30}, legend_title_text="")
    return figure


def tier_distribution(frame: pd.DataFrame) -> go.Figure:
    counts: pd.DataFrame = frame.groupby("risk_tier", as_index=False).agg(institutions=("cert", "size"))
    figure: go.Figure = px.bar(counts, x="risk_tier", y="institutions", color="risk_tier", color_discrete_map=TIER_COLORS)
    return finance_layout(figure, "Relative risk-tier distribution")


def category_alerts(frame: pd.DataFrame, column: str, title: str) -> go.Figure:
    grouped: pd.DataFrame = frame.groupby([column, "risk_tier"], as_index=False).agg(institutions=("cert", "size"))
    figure: go.Figure = px.bar(grouped, x=column, y="institutions", color="risk_tier", color_discrete_map=TIER_COLORS, barmode="stack")
    return finance_layout(figure, title)


def percentile_history(frame: pd.DataFrame) -> go.Figure:
    figure: go.Figure = px.line(frame.sort_values("reporting_date"), x="reporting_date", y="same_quarter_percentile", markers=True)
    figure.add_hline(y=95, line_dash="dash", line_color=COLORS["red"], annotation_text="Top-5% monitoring")
    figure.add_hline(y=99, line_dash="dot", line_color=COLORS["amber"], annotation_text="Top 1%")
    figure.update_yaxes(range=[0, 100], title="Same-quarter percentile")
    return finance_layout(figure, "Eight-quarter relative ranking history")


def feature_history(frame: pd.DataFrame, feature: str, label: str) -> go.Figure:
    figure: go.Figure = px.line(frame.sort_values("reporting_date"), x="reporting_date", y=feature, markers=True)
    figure.update_yaxes(title=label)
    return finance_layout(figure, label)


def peer_box(frame: pd.DataFrame, feature_label: str) -> go.Figure:
    row: pd.Series = frame.iloc[0]
    figure: go.Figure = go.Figure()
    figure.add_trace(go.Box(q1=[row["peer_p25"]], median=[row["peer_median"]], q3=[row["peer_p75"]],
                            lowerfence=[row["peer_p25"]], upperfence=[row["peer_p75"]], name="Same-quarter peers"))
    figure.add_trace(go.Scatter(x=["Same-quarter peers"], y=[row["feature_value"]], mode="markers",
                                marker={"size": 14, "color": COLORS["red"]}, name="Selected institution"))
    return finance_layout(figure, feature_label)


def validation_curve(frame: pd.DataFrame, section: str, title: str, x_title: str, y_title: str) -> go.Figure:
    subset: pd.DataFrame = frame.loc[frame["section"] == section].sort_values("x_value")
    figure: go.Figure = px.line(subset, x="x_value", y="y_value")
    if section in ("roc_curve", "calibration"):
        figure.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line={"dash": "dash", "color": COLORS["gray"]})
    figure.update_xaxes(title=x_title, range=[0, 1])
    figure.update_yaxes(title=y_title, range=[0, 1])
    return finance_layout(figure, title)


def lead_time_histogram(frame: pd.DataFrame) -> go.Figure:
    subset: pd.DataFrame = frame.loc[frame["section"] == "lead_time"]
    figure: go.Figure = px.histogram(subset, x="y_value", nbins=8)
    figure.update_xaxes(title="Lead days")
    figure.update_yaxes(title="Captured events")
    return finance_layout(figure, "Top-5% first-alert lead time")
