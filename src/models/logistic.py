"""Logistic candidate construction."""

from __future__ import annotations

from typing import Any

from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.pipeline import Pipeline

from .preprocessing import numeric_preprocessor


def logistic_pipeline(parameters: dict[str, Any], max_iter: int, seed: int) -> Pipeline:
    if str(parameters.get("optimizer", "")) == "sgd":
        regularized_model: SGDClassifier = SGDClassifier(
            loss="log_loss",
            penalty=str(parameters["penalty"]),
            alpha=float(parameters["alpha"]),
            l1_ratio=float(parameters.get("l1_ratio", 0.15)),
            class_weight="balanced",
            max_iter=max_iter,
            tol=1e-3,
            shuffle=True,
            random_state=seed,
            average=True,
        )
        return Pipeline([("preprocessor", numeric_preprocessor(True)), ("model", regularized_model)])
    model: LogisticRegression = LogisticRegression(
        C=float(parameters["C"]), solver=str(parameters["solver"]), l1_ratio=0.0,
        class_weight="balanced", max_iter=max_iter, random_state=seed,
    )
    return Pipeline([("preprocessor", numeric_preprocessor(True)), ("model", model)])
