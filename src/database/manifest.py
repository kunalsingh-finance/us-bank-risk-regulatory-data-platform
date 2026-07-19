"""Deterministic configuration and build-manifest utilities."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TypeAlias


JsonObject: TypeAlias = dict[str, object]


class ManifestError(ValueError):
    """Raised when configuration or manifest integrity fails."""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration_hash(config_without_hash: JsonObject) -> str:
    if "configuration_hash" in config_without_hash:
        raise ManifestError("configuration_hash must be excluded from its own digest")
    return sha256_bytes(canonical_json_bytes(config_without_hash))


def load_json_object(path: Path) -> JsonObject:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ManifestError(f"Configuration is not valid JSON-compatible YAML: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ManifestError(f"Configuration root must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def write_replaceable_json(path: Path, value: object) -> str:
    content: bytes = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)
    return sha256_bytes(content)

