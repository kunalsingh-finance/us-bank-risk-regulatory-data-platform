"""Local frozen-model perturbation explanations without outcome refitting."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.database.manifest import sha256_file
from src.models.trainer import FittedCandidate, predict_candidate


class DriverExplanationError(ValueError):
    """Raised when a local explanation cannot reconcile to a frozen score."""


def load_frozen_model(path: Path, expected_hash: str) -> FittedCandidate:
    observed: str = sha256_file(path)
    if observed != expected_hash:
        raise DriverExplanationError(f"Frozen model hash mismatch: expected={expected_hash}, observed={observed}, path={path}")
    with path.open("rb") as handle:
        model: object = pickle.load(handle)
    if not isinstance(model, FittedCandidate):
        raise TypeError(f"Unexpected frozen model type: {type(model)!r}")
    return model


def training_medians(model: FittedCandidate, feature_names: tuple[str, ...]) -> dict[str, float]:
    if not isinstance(model.artifact, Pipeline):
        raise TypeError("Frozen model artifact is not a scikit-learn Pipeline")
    preprocessor: Pipeline = model.artifact.named_steps["preprocessor"]
    statistics: np.ndarray = np.asarray(preprocessor.named_steps["imputer"].statistics_, dtype=float)
    if len(statistics) < len(feature_names):
        raise DriverExplanationError(f"Training median count is too small: medians={len(statistics)}, features={len(feature_names)}")
    return {name: float(statistics[index]) for index, name in enumerate(feature_names)}


def local_perturbation_drivers(
    model: FittedCandidate,
    frame: pd.DataFrame,
    feature_names: tuple[str, ...],
    explanation_features: tuple[str, ...],
    frozen_scores: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features: pd.DataFrame = frame.loc[:, feature_names].astype(float).replace([np.inf, -np.inf], np.nan)
    predicted: np.ndarray = predict_candidate(model, features)
    difference: np.ndarray = np.abs(predicted - frozen_scores)
    maximum_difference: float = float(difference.max()) if len(difference) else 0.0
    if maximum_difference > 1e-12:
        raise DriverExplanationError(f"Frozen score reconciliation failed: maximum_absolute_difference={maximum_difference}")
    medians: dict[str, float] = training_medians(model, feature_names)
    contributions: np.ndarray = np.empty((len(frame), len(explanation_features)), dtype=float)
    for index, feature_name in enumerate(explanation_features):
        perturbed: pd.DataFrame = features.copy()
        perturbed[feature_name] = medians[feature_name]
        counterfactual: np.ndarray = predict_candidate(model, perturbed)
        contributions[:, index] = predicted - counterfactual
    absolute: np.ndarray = np.abs(contributions)
    top_indices: np.ndarray = np.argsort(-absolute, axis=1, kind="stable")[:, :3]
    explanation_values: np.ndarray = features.loc[:, explanation_features].to_numpy(dtype=float)
    rows: list[pd.DataFrame] = []
    identifiers: pd.DataFrame = frame[["cert", "rssdid", "reporting_date"]].reset_index(drop=True)
    for rank in range(3):
        indices: np.ndarray = top_indices[:, rank]
        names: np.ndarray = np.asarray(explanation_features, dtype=object)[indices]
        deltas: np.ndarray = contributions[np.arange(len(frame)), indices]
        values: np.ndarray = explanation_values[np.arange(len(frame)), indices]
        baselines: np.ndarray = np.asarray([medians[str(name)] for name in names], dtype=float)
        result: pd.DataFrame = identifiers.copy()
        result["driver_rank"] = rank + 1
        result["feature_name"] = names
        result["score_delta"] = deltas
        result["driver_direction"] = np.where(deltas > 0.0, "Increased ranking score", np.where(deltas < 0.0, "Decreased ranking score", "No measurable score change"))
        result["current_feature_value"] = values
        result["training_median_reference"] = baselines
        result["explanation_method"] = "Single-feature training-median perturbation on frozen model"
        rows.append(result)
    drivers: pd.DataFrame = pd.concat(rows, ignore_index=True).sort_values(["reporting_date", "cert", "driver_rank"]).reset_index(drop=True)
    validation: pd.DataFrame = pd.DataFrame([{
        "control_id": "DRV001", "control_name": "Frozen score equality",
        "observations": len(frame), "maximum_absolute_difference": maximum_difference,
        "status": "PASS", "evidence": "Frozen model reproduced raw stored scores before local perturbation",
    }])
    return drivers, validation
