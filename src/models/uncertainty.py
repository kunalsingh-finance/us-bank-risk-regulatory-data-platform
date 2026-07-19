"""Institution-clustered and unique-event bootstrap intervals."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def institution_cluster_bootstrap(
    predictions: pd.DataFrame,
    repetitions: int,
    seed: int,
) -> pd.DataFrame:
    rng: np.random.Generator = np.random.default_rng(seed)
    certs: np.ndarray = predictions["cert"].drop_duplicates().to_numpy()
    rows: list[dict[str, float | int]] = []
    grouped: dict[object, pd.DataFrame] = {key: value for key, value in predictions.groupby("cert")}
    for repetition in range(repetitions):
        sampled: np.ndarray = rng.choice(certs, size=len(certs), replace=True)
        frame: pd.DataFrame = pd.concat([grouped[cert] for cert in sampled], ignore_index=True)
        y: np.ndarray = frame["target"].to_numpy(dtype=int)
        p: np.ndarray = frame["probability"].to_numpy(dtype=float)
        if np.unique(y).size < 2:
            continue
        rows.append({"repetition": repetition, "average_precision": float(average_precision_score(y,p)), "roc_auc": float(roc_auc_score(y,p)), "brier_score": float(brier_score_loss(y,p))})
    return pd.DataFrame(rows)


def confidence_intervals(draws: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for metric in ("average_precision", "roc_auc", "brier_score"):
        rows.append({"metric": metric, "lower_95": float(draws[metric].quantile(0.025)), "median": float(draws[metric].median()), "upper_95": float(draws[metric].quantile(0.975))})
    return pd.DataFrame(rows)


def event_bootstrap(events: pd.DataFrame, repetitions: int, seed: int, budgets: tuple[float, ...]) -> pd.DataFrame:
    rng: np.random.Generator = np.random.default_rng(seed)
    rows: list[dict[str, float | int]] = []
    for repetition in range(repetitions):
        sample: pd.DataFrame = events.iloc[rng.integers(0, len(events), len(events))]
        record: dict[str, float | int] = {"repetition": repetition}
        for budget in budgets:
            record[f"capture_top_{int(budget*100)}pct"] = float(sample[f"captured_top_{int(budget*100)}pct"].mean())
        rows.append(record)
    return pd.DataFrame(rows)
