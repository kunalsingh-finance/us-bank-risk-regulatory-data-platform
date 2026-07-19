"""Strict configuration loading for Phase 5."""

from __future__ import annotations

from pathlib import Path

from src.database.manifest import JsonObject, configuration_hash, load_json_object


class ModelConfigurationError(ValueError):
    """Raised when a frozen model configuration is invalid."""


def load_hashed_config(path: Path) -> JsonObject:
    config: JsonObject = load_json_object(path)
    stored: object = config.get("configuration_hash")
    if not isinstance(stored, str):
        raise ModelConfigurationError(f"Missing configuration_hash: {path}")
    calculated: str = configuration_hash({key: value for key, value in config.items() if key != "configuration_hash"})
    if stored != calculated:
        raise ModelConfigurationError(
            f"Configuration hash mismatch: path={path}, stored={stored}, calculated={calculated}"
        )
    return config


def require_string(config: JsonObject, key: str) -> str:
    value: object = config.get(key)
    if not isinstance(value, str):
        raise ModelConfigurationError(f"Expected string {key}; received {value!r}")
    return value


def require_list(config: JsonObject, key: str) -> list[object]:
    value: object = config.get(key)
    if not isinstance(value, list):
        raise ModelConfigurationError(f"Expected list {key}; received {value!r}")
    return value


def included_features(config: JsonObject) -> tuple[str, ...]:
    value: object = config.get("included_feature_names")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ModelConfigurationError("included_feature_names must be a string list")
    names: tuple[str, ...] = tuple(str(item) for item in value)
    if len(names) != len(set(names)):
        raise ModelConfigurationError("Included feature names are not unique")
    return names
