"""Phase 4 configuration and manifest helpers."""

from __future__ import annotations

from pathlib import Path

from src.database.manifest import JsonObject, configuration_hash, load_json_object


class LabelConfigurationError(ValueError):
    """Raised when a frozen label configuration is invalid."""


def load_hashed_configuration(path: Path) -> JsonObject:
    config: JsonObject = load_json_object(path)
    stored: object = config.get("configuration_hash")
    if not isinstance(stored, str):
        raise LabelConfigurationError(f"Missing configuration_hash: {path}")
    calculated: str = configuration_hash({key: value for key, value in config.items() if key != "configuration_hash"})
    if stored != calculated:
        raise LabelConfigurationError(
            f"Configuration hash mismatch: path={path}, stored={stored}, calculated={calculated}"
        )
    return config


def require_string(config: JsonObject, key: str) -> str:
    value: object = config.get(key)
    if not isinstance(value, str):
        raise LabelConfigurationError(f"Expected string {key}; received {value!r}")
    return value


def require_int(config: JsonObject, key: str) -> int:
    value: object = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LabelConfigurationError(f"Expected integer {key}; received {value!r}")
    return value


def require_string_list(config: JsonObject, key: str) -> tuple[str, ...]:
    value: object = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LabelConfigurationError(f"Expected string list {key}; received {value!r}")
    return tuple(str(item) for item in value)
