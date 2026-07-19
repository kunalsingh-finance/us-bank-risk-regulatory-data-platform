"""Strict dashboard configuration loading."""

from __future__ import annotations

from pathlib import Path

from src.database.manifest import JsonObject
from src.models.config import load_hashed_config, require_list, require_string


def load_dashboard_configs(root: Path) -> tuple[JsonObject, JsonObject, JsonObject, JsonObject]:
    dashboard: JsonObject = load_hashed_config(root / "configs/dashboard.yaml")
    tiers: JsonObject = load_hashed_config(root / "configs/dashboard_risk_tiers.yaml")
    cases: JsonObject = load_hashed_config(root / "configs/dashboard_case_studies.yaml")
    disclaimers: JsonObject = load_hashed_config(root / "configs/dashboard_disclaimers.yaml")
    require_string(dashboard, "dashboard_build_run_id")
    require_string(dashboard, "frozen_model_version")
    require_list(dashboard, "history_features")
    require_list(tiers, "tiers")
    require_list(cases, "roles")
    require_string(disclaimers, "persistent")
    return dashboard, tiers, cases, disclaimers


def string_list(config: JsonObject, key: str) -> tuple[str, ...]:
    values: list[object] = require_list(config, key)
    if not all(isinstance(value, str) for value in values):
        raise TypeError(f"Dashboard configuration field must contain strings: key={key}")
    return tuple(str(value) for value in values)
