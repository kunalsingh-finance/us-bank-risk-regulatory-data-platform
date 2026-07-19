"""Training-only preprocessing pipelines."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def numeric_preprocessor(scale: bool) -> Pipeline:
    steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median", add_indicator=True))]
    if scale:
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps)


def fitted_training_medians(pipeline: Pipeline) -> np.ndarray:
    imputer: SimpleImputer = pipeline.named_steps["imputer"]
    if not hasattr(imputer, "statistics_"):
        raise ValueError("Preprocessor is not fitted")
    return np.asarray(imputer.statistics_, dtype=float)
