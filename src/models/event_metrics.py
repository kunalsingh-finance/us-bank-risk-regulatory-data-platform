"""Unique-failure-event capture and lead-time evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .thresholds import quarter_budget_flags


def failure_event_capture(
    predictions: pd.DataFrame,
    budgets: tuple[float, ...],
) -> pd.DataFrame:
    frame: pd.DataFrame = predictions.copy()
    for fraction in budgets:
        frame[f"flag_{int(fraction*100)}pct"] = quarter_budget_flags(
            frame[["cert", "reporting_date"]], frame["probability"].to_numpy(), fraction
        )
    positive: pd.DataFrame = frame.loc[frame["target"] == 1].copy()
    rows: list[dict[str, object]] = []
    for (cert, event_date), group in positive.groupby(["cert", "next_failure_date"], dropna=False):
        record: dict[str, object] = {
            "cert": int(cert), "failure_date": event_date,
            "maximum_pre_failure_score": float(group["probability"].max()),
        }
        for fraction in budgets:
            suffix: str = f"{int(fraction*100)}pct"
            flagged: pd.DataFrame = group.loc[group[f"flag_{suffix}"]]
            record[f"captured_top_{suffix}"] = not flagged.empty
            record[f"earliest_alert_top_{suffix}"] = flagged["reporting_date"].min() if not flagged.empty else pd.NaT
            record[f"lead_days_top_{suffix}"] = int((pd.Timestamp(event_date) - pd.Timestamp(flagged["reporting_date"].min())).days) if not flagged.empty else None
            record[f"alerted_quarters_top_{suffix}"] = int(len(flagged))
        rows.append(record)
    return pd.DataFrame(rows).sort_values(["failure_date", "cert"]).reset_index(drop=True)


def event_capture_rate(events: pd.DataFrame, budget: float) -> float:
    column: str = f"captured_top_{int(budget*100)}pct"
    return float(np.mean(events[column].astype(bool))) if len(events) else 0.0
