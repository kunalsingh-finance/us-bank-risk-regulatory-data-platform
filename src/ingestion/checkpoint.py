"""Checkpoint persistence for resumable FDIC downloads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .manifest import write_replaceable_json


class CheckpointError(ValueError):
    """Raised when a checkpoint is malformed or belongs to another query."""


@dataclass(frozen=True)
class DownloadCheckpoint:
    query_hash: str
    next_offset: int
    expected_total: int
    page_hashes: tuple[str, ...]


def load_checkpoint(path: Path, expected_query_hash: str) -> DownloadCheckpoint | None:
    if not path.exists():
        return None
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CheckpointError(f"Checkpoint is not valid JSON: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise CheckpointError(f"Checkpoint root must be an object: {path}")
    query_hash: object = payload.get("query_hash")
    next_offset: object = payload.get("next_offset")
    expected_total: object = payload.get("expected_total")
    page_hashes: object = payload.get("page_hashes")
    if query_hash != expected_query_hash:
        raise CheckpointError(
            f"Checkpoint query hash {query_hash!r} does not match {expected_query_hash}"
        )
    if not isinstance(next_offset, int) or not isinstance(expected_total, int):
        raise CheckpointError(f"Checkpoint offsets/totals must be integers: {path}")
    if not isinstance(page_hashes, list) or not all(
        isinstance(value, str) for value in page_hashes
    ):
        raise CheckpointError(f"Checkpoint page_hashes must be a string array: {path}")
    return DownloadCheckpoint(
        query_hash=expected_query_hash,
        next_offset=next_offset,
        expected_total=expected_total,
        page_hashes=tuple(page_hashes),
    )


def save_checkpoint(path: Path, checkpoint: DownloadCheckpoint) -> str:
    return write_replaceable_json(path, asdict(checkpoint))

