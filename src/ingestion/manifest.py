"""Deterministic hashing and write-once file utilities for ingestion lineage."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class ImmutableFileConflictError(FileExistsError):
    """Raised when an existing immutable file differs from new content."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def write_once(path: Path, content: bytes) -> str:
    content_hash: str = sha256_bytes(content)
    if path.exists():
        existing_hash: str = sha256_file(path)
        if existing_hash != content_hash:
            raise ImmutableFileConflictError(
                f"Refusing to overwrite {path}; existing SHA-256 {existing_hash}, new {content_hash}"
            )
        return existing_hash
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)
    return content_hash


def write_json_once(path: Path, value: object) -> str:
    return write_once(path, canonical_json_bytes(value))


def write_replaceable_json(path: Path, value: object) -> str:
    content: bytes = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)
    return sha256_bytes(content)

