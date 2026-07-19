"""Prevalence and preregistered transparent-rule baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit


def prevalence_probability(y_train: np.ndarray, observation_count: int) -> np.ndarray:
    prevalence: float = float(np.mean(y_train))
    return np.full(observation_count, prevalence, dtype=float)


def fit_rule_parameters(frame: pd.DataFrame, feature_names: tuple[str, ...]) -> dict[str, np.ndarray]:
    values: np.ndarray = frame.loc[:, feature_names].astype(float).to_numpy()
    medians: np.ndarray = np.nanmedian(values, axis=0)
    filled: np.ndarray = np.where(np.isnan(values), medians, values)
    means: np.ndarray = filled.mean(axis=0)
    scales: np.ndarray = filled.std(axis=0)
    scales = np.where(scales <= 1e-12, 1.0, scales)
    return {"medians": medians, "means": means, "scales": scales}


def rule_probability(
    frame: pd.DataFrame,
    feature_names: tuple[str, ...],
    parameters: dict[str, np.ndarray],
) -> np.ndarray:
    values: np.ndarray = frame.loc[:, feature_names].astype(float).to_numpy()
    filled: np.ndarray = np.where(np.isnan(values), parameters["medians"], values)
    z: np.ndarray = (filled - parameters["means"]) / parameters["scales"]
    directions: np.ndarray = np.asarray([-1.0, 1.0, -1.0, 1.0, 1.0, 1.0])
    return expit(np.mean(z * directions, axis=1))
