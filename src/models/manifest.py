"""Manifest and hashing helpers for governed model experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.database.manifest import JsonObject, sha256_file, write_replaceable_json


def canonical_hash(value: object) -> str:
    payload: bytes = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def code_hash(paths: tuple[Path, ...]) -> str:
    items: list[dict[str, str]] = [
        {"path": path.as_posix(), "sha256": sha256_file(path)} for path in sorted(paths)
    ]
    return canonical_hash(items)


def write_manifest(path: Path, payload: JsonObject) -> None:
    write_replaceable_json(path, payload)
