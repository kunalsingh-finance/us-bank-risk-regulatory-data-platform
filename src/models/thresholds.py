"""Validation-only classification and same-quarter alert-budget thresholds."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.metrics import fbeta_score


def select_f2_threshold(y_true: np.ndarray, probability: np.ndarray) -> float:
    candidates: np.ndarray = np.unique(np.quantile(probability, np.linspace(0.70, 0.999, 200)))
    scored: list[tuple[float, float]] = []
    for threshold in candidates:
        prediction: np.ndarray = (probability >= threshold).astype(int)
        scored.append((float(fbeta_score(y_true, prediction, beta=2, zero_division=0)), float(threshold)))
    return max(scored, key=lambda item: (item[0], item[1]))[1]


def quarter_budget_flags(
    identifiers: pd.DataFrame,
    probability: np.ndarray,
    fraction: float,
) -> np.ndarray:
    if not 0 < fraction <= 1:
        raise ValueError(f"Alert fraction must be in (0,1]: {fraction}")
    work: pd.DataFrame = identifiers.loc[:, ["cert", "reporting_date"]].copy()
    work["probability"] = probability
    work["original_index"] = np.arange(len(work))
    work = work.sort_values(["reporting_date", "probability", "cert"], ascending=[True, False, True])
    work["quarter_count"] = work.groupby("reporting_date")["cert"].transform("count")
    work["rank"] = work.groupby("reporting_date").cumcount() + 1
    work["budget_count"] = work["quarter_count"].map(lambda value: max(1, math.ceil(int(value) * fraction)))
    work["flag"] = work["rank"] <= work["budget_count"]
    return work.sort_values("original_index")["flag"].to_numpy(dtype=bool)
