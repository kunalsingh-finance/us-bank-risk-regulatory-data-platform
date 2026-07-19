"""Time-safe probability calibration fitted on the configured calibration period."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def probability_logit(probability: np.ndarray) -> np.ndarray:
    clipped: np.ndarray = np.clip(probability, 1e-8, 1 - 1e-8)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_calibrator(method: str, y_true: np.ndarray, probability: np.ndarray) -> dict[str, Any]:
    if method == "none":
        return {"method": method, "model": None}
    if method == "platt":
        model: LogisticRegression = LogisticRegression(C=1e6, max_iter=1000)
        model.fit(probability_logit(probability), y_true)
        return {"method": method, "model": model}
    if method == "isotonic":
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(probability, y_true)
        return {"method": method, "model": model}
    raise ValueError(f"Unsupported calibration method: {method}")


def apply_calibrator(calibrator: dict[str, Any], probability: np.ndarray) -> np.ndarray:
    method: str = str(calibrator["method"])
    model: Any = calibrator["model"]
    if method == "none":
        return np.asarray(probability, dtype=float)
    if method == "platt":
        return np.asarray(model.predict_proba(probability_logit(probability))[:, 1], dtype=float)
    if method == "isotonic":
        return np.asarray(model.predict(probability), dtype=float)
    raise ValueError(f"Unsupported calibration method: {method}")
