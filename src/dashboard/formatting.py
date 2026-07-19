"""Consistent dashboard labels and value formatting."""

from __future__ import annotations


ASSET_BAND_LABELS: dict[str, str] = {
    "LT_100M": "Less than $100M", "100M_500M": "$100M–$500M", "500M_1B": "$500M–$1B",
    "1B_10B": "$1B–$10B", "10B_50B": "$10B–$50B", "50B_250B": "$50B–$250B", "GE_250B": "$250B+",
}


def percentile_label(value: float) -> str:
    return f"{value:.1f}th"


def feature_label(name: str) -> str:
    return name.replace("_", " ").title().replace("Qoq", "QoQ").replace("Yoy", "YoY").replace("Roa", "ROA")
