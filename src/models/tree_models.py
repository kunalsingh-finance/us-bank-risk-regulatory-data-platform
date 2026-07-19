"""Constrained tree-model candidate construction."""

from __future__ import annotations

from typing import Any

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.pipeline import Pipeline

from .preprocessing import numeric_preprocessor


def random_forest_pipeline(parameters: dict[str, Any], seed: int) -> Pipeline:
    model: RandomForestClassifier = RandomForestClassifier(
        n_estimators=int(parameters["n_estimators"]), max_depth=int(parameters["max_depth"]),
        min_samples_leaf=int(parameters["min_samples_leaf"]), max_features=str(parameters["max_features"]),
        class_weight="balanced_subsample", random_state=seed, n_jobs=-1,
    )
    return Pipeline([("preprocessor", numeric_preprocessor(False)), ("model", model)])


def gradient_boosting_pipeline(parameters: dict[str, Any], seed: int) -> Pipeline:
    model: HistGradientBoostingClassifier = HistGradientBoostingClassifier(
        learning_rate=float(parameters["learning_rate"]), max_iter=int(parameters["max_iter"]),
        max_leaf_nodes=int(parameters["max_leaf_nodes"]), min_samples_leaf=int(parameters["min_samples_leaf"]),
        l2_regularization=float(parameters["l2_regularization"]), class_weight="balanced",
        random_state=seed,
    )
    return Pipeline([("preprocessor", numeric_preprocessor(False)), ("model", model)])
