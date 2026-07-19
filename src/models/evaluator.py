"""Observation-level rare-event metrics and calibration diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .calibration import probability_logit
from .thresholds import quarter_budget_flags


def expected_calibration_error(y_true: np.ndarray, probability: np.ndarray, bins: int) -> float:
    edges: np.ndarray = np.linspace(0.0, 1.0, bins + 1)
    assignments: np.ndarray = np.clip(np.digitize(probability, edges, right=True) - 1, 0, bins - 1)
    result: float = 0.0
    for index in range(bins):
        mask: np.ndarray = assignments == index
        if mask.any():
            result += float(mask.mean()) * abs(float(y_true[mask].mean()) - float(probability[mask].mean()))
    return result


def calibration_intercept_slope(y_true: np.ndarray, probability: np.ndarray) -> tuple[float, float]:
    if np.unique(y_true).size < 2:
        return float("nan"), float("nan")
    model: LogisticRegression = LogisticRegression(C=1e6, max_iter=1000)
    model.fit(probability_logit(probability), y_true)
    return float(model.intercept_[0]), float(model.coef_[0, 0])


def evaluate_predictions(
    identifiers: pd.DataFrame,
    y_true: np.ndarray,
    probability: np.ndarray,
    threshold: float,
    budgets: tuple[float, ...],
) -> dict[str, Any]:
    prediction: np.ndarray = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    intercept, slope = calibration_intercept_slope(y_true, probability)
    result: dict[str, Any] = {
        "observations": int(len(y_true)), "positives": int(y_true.sum()), "negatives": int((1-y_true).sum()),
        "positive_rate": float(y_true.mean()), "average_precision": float(average_precision_score(y_true, probability)),
        "baseline_average_precision": float(y_true.mean()), "roc_auc": float(roc_auc_score(y_true, probability)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "log_loss": float(log_loss(y_true, probability, labels=[0, 1])),
        "calibration_intercept": intercept, "calibration_slope": slope,
        "expected_calibration_error": expected_calibration_error(y_true, probability, 10),
        "threshold": float(threshold), "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "f2": float(fbeta_score(y_true, prediction, beta=2, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "matthews_correlation_coefficient": float(matthews_corrcoef(y_true, prediction)),
        "accuracy_with_warning": float(accuracy_score(y_true, prediction)),
    }
    for fraction in budgets:
        flags: np.ndarray = quarter_budget_flags(identifiers, probability, fraction)
        alerts: int = int(flags.sum())
        captured: int = int(y_true[flags].sum())
        suffix: str = f"top_{int(fraction*100)}pct"
        result[f"{suffix}_alerts"] = alerts
        result[f"{suffix}_false_alerts"] = int(alerts - captured)
        result[f"{suffix}_precision"] = float(captured / alerts) if alerts else 0.0
        result[f"{suffix}_recall"] = float(captured / y_true.sum()) if y_true.sum() else 0.0
    return result


def reliability_table(y_true: np.ndarray, probability: np.ndarray, bins: int) -> pd.DataFrame:
    frame: pd.DataFrame = pd.DataFrame({"target": y_true, "probability": probability})
    frame["bin"] = pd.cut(frame["probability"], bins=np.linspace(0, 1, bins+1), include_lowest=True, duplicates="drop")
    return frame.groupby("bin", observed=True).agg(observations=("target","size"), positives=("target","sum"), mean_probability=("probability","mean"), observed_rate=("target","mean")).reset_index().astype({"bin":"string"})
