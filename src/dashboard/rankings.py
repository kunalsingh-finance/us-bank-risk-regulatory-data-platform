"""Pure same-quarter ranking and transparent tier functions."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def current_review_population(scores: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    """Keep the whole latest-quarter population before applying a review budget."""
    population = scores.copy()
    population["reporting_date"] = pd.to_datetime(population["reporting_date"])
    population = population.loc[population["reporting_date"].eq(population["reporting_date"].max())].copy()
    explanations = drivers.copy()
    explanations["reporting_date"] = pd.to_datetime(explanations["reporting_date"])
    explanations = explanations.loc[
        explanations["reporting_date"].eq(population["reporting_date"].max())
        & explanations["driver_rank"].isin([1, 2, 3])
    ]
    keys = ["cert", "reporting_date"]
    if explanations.empty:
        for rank in (1, 2, 3):
            population[f"top_driver_{rank}"] = "Unavailable"
    else:
        pivoted = explanations.pivot(index=keys, columns="driver_rank", values="feature_name")
        pivoted = pivoted.reindex(columns=[1, 2, 3]).rename(columns=lambda rank: f"top_driver_{rank}")
        population = population.merge(pivoted.reset_index(), on=keys, how="left", validate="one_to_one")
        for rank in (1, 2, 3):
            population[f"top_driver_{rank}"] = population[f"top_driver_{rank}"].fillna("Unavailable")
    return population.sort_values(["same_quarter_rank", "cert"]).reset_index(drop=True)


def risk_tier(percentile: float) -> str:
    if percentile < 0.0 or percentile > 100.0:
        raise ValueError(f"Percentile outside 0-100: {percentile}")
    if percentile < 50.0:
        return "Low"
    if percentile < 90.0:
        return "Moderate"
    if percentile < 95.0:
        return "Elevated"
    if percentile < 99.0:
        return "High"
    return "Highest monitored tier"


def alert_status(percentile: float, top_5_percent_flag: bool) -> str:
    if top_5_percent_flag:
        return "Top-5% review"
    if percentile >= 90.0:
        return "Elevated indicators"
    if percentile >= 50.0:
        return "Monitor"
    return "No alert"


def rank_same_quarter(frame: pd.DataFrame) -> pd.DataFrame:
    required: set[str] = {"cert", "reporting_date", "model_score"}
    missing: set[str] = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Ranking input missing columns: {sorted(missing)}")
    output: pd.DataFrame = frame.copy()
    output["reporting_date"] = pd.to_datetime(output["reporting_date"])
    output["scored_population"] = output.groupby("reporting_date")["cert"].transform("count")
    output["same_quarter_rank"] = output.groupby("reporting_date")["model_score"].rank(method="min", ascending=False).astype(int)
    output["same_quarter_percentile"] = output.groupby("reporting_date")["model_score"].rank(method="min", pct=True, ascending=True).sub(
        output.groupby("reporting_date")["model_score"].transform(lambda values: 1.0 / len(values))
    )
    denominator: pd.Series = (output["scored_population"] - 1).clip(lower=1)
    output["same_quarter_percentile"] = 100.0 * output.groupby("reporting_date")["model_score"].rank(method="min", ascending=True).sub(1) / denominator
    ordered: pd.DataFrame = output.sort_values(["reporting_date", "model_score", "cert"], ascending=[True, False, True]).copy()
    ordered["budget_rank"] = ordered.groupby("reporting_date").cumcount() + 1
    for percentage in (1, 5, 10):
        limit: pd.Series = ordered["scored_population"].map(lambda count: max(1, math.ceil(int(count) * percentage / 100.0)))
        ordered[f"top_{percentage}_percent_flag"] = ordered["budget_rank"] <= limit
    ordered["risk_tier"] = ordered["same_quarter_percentile"].map(risk_tier)
    ordered["alert_status"] = [alert_status(float(percentile), bool(flag)) for percentile, flag in zip(ordered["same_quarter_percentile"], ordered["top_5_percent_flag"], strict=True)]
    return ordered.sort_index()


def percentile_changes(frame: pd.DataFrame) -> pd.DataFrame:
    output: pd.DataFrame = frame.copy()
    output["reporting_date"] = pd.to_datetime(output["reporting_date"])
    lookup: pd.DataFrame = output[["cert", "reporting_date", "same_quarter_percentile"]].rename(columns={"same_quarter_percentile": "lookup_percentile"})
    prior: pd.DataFrame = lookup.copy()
    prior["reporting_date"] = prior["reporting_date"] + pd.offsets.QuarterEnd()
    prior = prior.rename(columns={"lookup_percentile": "prior_quarter_percentile"})
    year: pd.DataFrame = lookup.copy()
    year["reporting_date"] = year["reporting_date"] + pd.offsets.QuarterEnd(4)
    year = year.rename(columns={"lookup_percentile": "four_quarter_prior_percentile"})
    output = output.merge(prior, on=["cert", "reporting_date"], how="left").merge(year, on=["cert", "reporting_date"], how="left")
    output["percentile_change_qoq"] = output["same_quarter_percentile"] - output["prior_quarter_percentile"]
    output["percentile_change_yoy"] = output["same_quarter_percentile"] - output["four_quarter_prior_percentile"]
    return output


def no_infinite(values: pd.Series) -> bool:
    numeric: np.ndarray = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    return bool(not np.isinf(numeric).any())
