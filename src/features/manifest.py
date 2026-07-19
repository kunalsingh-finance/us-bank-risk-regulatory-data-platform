"""Phase 3 manifest types and configuration validation."""

from __future__ import annotations

from pathlib import Path

from src.database.manifest import JsonObject, configuration_hash, load_json_object


class FeatureConfigurationError(ValueError):
    """Raised when a Phase 3 configuration is invalid or self-hash does not reconcile."""


def load_hashed_configuration(path: Path) -> JsonObject:
    config: JsonObject = load_json_object(path)
    stored: object = config.get("configuration_hash")
    if not isinstance(stored, str):
        raise FeatureConfigurationError(f"Missing configuration_hash: {path}")
    calculated: str = configuration_hash({key: value for key, value in config.items() if key != "configuration_hash"})
    if stored != calculated:
        raise FeatureConfigurationError(
            f"Configuration hash mismatch: path={path}, stored={stored}, calculated={calculated}"
        )
    return config


def require_string(config: JsonObject, key: str) -> str:
    value: object = config.get(key)
    if not isinstance(value, str):
        raise FeatureConfigurationError(f"Expected string configuration value {key}; received {value!r}")
    return value


def require_int(config: JsonObject, key: str) -> int:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise FeatureConfigurationError(f"Expected integer configuration value {key}; received {value!r}")
    return value


def require_string_list(config: JsonObject, key: str) -> tuple[str, ...]:
    value: object = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FeatureConfigurationError(f"Expected string list {key}; received {value!r}")
    return tuple(str(item) for item in value)
