"""Dashboard artifact hashing and manifest helpers."""

from __future__ import annotations

from pathlib import Path

from src.database.manifest import JsonObject, sha256_file, write_replaceable_json
from src.models.manifest import canonical_hash


def file_inventory(root: Path, paths: tuple[Path, ...]) -> list[JsonObject]:
    return [
        {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        for path in sorted(paths)
    ]


def write_dashboard_manifest(path: Path, payload: JsonObject) -> None:
    governed: JsonObject = dict(payload)
    governed["manifest_content_hash"] = canonical_hash(payload)
    write_replaceable_json(path, governed)
