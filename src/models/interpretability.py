"""Coefficient and tree-importance extraction."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline


def logistic_coefficients(model: Pipeline, feature_names: tuple[str, ...]) -> pd.DataFrame:
    fitted = model.named_steps["model"]
    coefficient: np.ndarray = np.asarray(fitted.coef_[0], dtype=float)
    names: list[str] = list(feature_names) + [f"missing__{index}" for index in range(len(coefficient)-len(feature_names))]
    return pd.DataFrame({"feature_name": names, "standardized_coefficient": coefficient, "odds_ratio": np.exp(np.clip(coefficient,-20,20)), "importance_type": "coefficient"})


def permutation_importance_frame(
    model: Pipeline,
    features: pd.DataFrame,
    target: np.ndarray,
    feature_names: tuple[str, ...],
    seed: int,
) -> pd.DataFrame:
    result = permutation_importance(model, features, target, scoring="average_precision", n_repeats=3, random_state=seed, n_jobs=-1)
    return pd.DataFrame({"feature_name": feature_names, "importance_mean": result.importances_mean, "importance_std": result.importances_std, "importance_type": "permutation_average_precision"}).sort_values("importance_mean", ascending=False)
