"""Resumable page assembly for FDIC Financials anchor-quarter probes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .checkpoint import DownloadCheckpoint, load_checkpoint, save_checkpoint
from .fdic_client import FdicClient, FinancialsQuery, replace_offset
from .manifest import canonical_json_bytes, sha256_bytes, write_json_once, write_once
from .schema import Record, ValidatedPage, find_duplicate_bank_quarters, validate_quarter_end, validate_response


class DownloadValidationError(RuntimeError):
    """Raised when page assembly or reconciliation fails."""


@dataclass(frozen=True)
class PageManifest:
    offset: int
    requested_limit: int
    row_count: int
    expected_total: int
    response_sha256: str
    request_url: str
    attempts: int
    index_name: str
    index_created_at: str


@dataclass(frozen=True)
class DownloadResult:
    records: list[Record]
    pages: tuple[PageManifest, ...]
    total: int
    query_hash: str


def query_identity(endpoint: str, query: FinancialsQuery) -> str:
    payload: dict[str, object] = {
        "endpoint": endpoint,
        "filters": query.filters,
        "fields": list(query.fields),
        "sort_by": query.sort_by,
        "sort_order": query.sort_order,
        "limit": query.limit,
        "format": query.output_format,
    }
    return sha256_bytes(canonical_json_bytes(payload))


def load_saved_page(
    path: Path,
    requested_fields: frozenset[str],
    required_fields: frozenset[str],
    allowed_unexpected_fields: frozenset[str],
) -> ValidatedPage:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DownloadValidationError(f"Saved page is invalid JSON: {path}: {error}") from error
    return validate_response(
        payload=payload,
        required_fields=required_fields,
        requested_fields=requested_fields,
        allowed_unexpected_fields=allowed_unexpected_fields,
    )


def assemble_saved_pages(
    output_dir: Path,
    requested_fields: frozenset[str],
    required_fields: frozenset[str],
    allowed_unexpected_fields: frozenset[str],
    expected_total: int,
) -> list[Record]:
    page_paths: list[Path] = sorted(
        path for path in output_dir.glob("page_*.json") if not path.name.endswith(".manifest.json")
    )
    records: list[Record] = []
    for page_path in page_paths:
        page: ValidatedPage = load_saved_page(
            path=page_path,
            requested_fields=requested_fields,
            required_fields=required_fields,
            allowed_unexpected_fields=allowed_unexpected_fields,
        )
        if page.total != expected_total:
            raise DownloadValidationError(
                f"Page total changed within run: path={page_path}, page_total={page.total}, "
                f"expected_total={expected_total}"
            )
        records.extend(page.records)
    if len(records) != expected_total:
        raise DownloadValidationError(
            f"Assembled row count {len(records)} does not equal API total {expected_total}"
        )
    return records


def download_query(
    client: FdicClient,
    endpoint: str,
    query: FinancialsQuery,
    output_dir: Path,
    checkpoint_path: Path,
    expected_report_date: str,
    required_fields: frozenset[str],
    allowed_unexpected_fields: frozenset[str],
) -> DownloadResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    identity: str = query_identity(endpoint=endpoint, query=query)
    checkpoint: DownloadCheckpoint | None = load_checkpoint(
        path=checkpoint_path, expected_query_hash=identity
    )
    offset: int = 0 if checkpoint is None else checkpoint.next_offset
    expected_total: int | None = None if checkpoint is None else checkpoint.expected_total
    page_hashes: list[str] = [] if checkpoint is None else list(checkpoint.page_hashes)
    page_manifests: list[PageManifest] = []
    while expected_total is None or offset < expected_total:
        page_query: FinancialsQuery = replace_offset(query=query, offset=offset)
        fetched = client.fetch_page(endpoint=endpoint, query=page_query)
        page: ValidatedPage = fetched.validated
        if expected_total is None:
            expected_total = page.total
        elif page.total != expected_total:
            raise DownloadValidationError(
                f"API total changed during pagination: prior={expected_total}, current={page.total}, "
                f"offset={offset}"
            )
        if not page.records and offset < expected_total:
            raise DownloadValidationError(
                f"Empty page before expected total: offset={offset}, total={expected_total}"
            )
        for record in page.records:
            validate_quarter_end(record.get("REPDTE"), expected_report_date)
        response_hash: str = sha256_bytes(fetched.body)
        if response_hash in page_hashes:
            raise DownloadValidationError(
                f"Duplicate page response detected: offset={offset}, sha256={response_hash}"
            )
        page_path: Path = output_dir / f"page_{offset:08d}.json"
        write_once(path=page_path, content=fetched.body)
        manifest = PageManifest(
            offset=offset,
            requested_limit=query.limit,
            row_count=len(page.records),
            expected_total=expected_total,
            response_sha256=response_hash,
            request_url=fetched.url,
            attempts=fetched.attempts,
            index_name=page.index_name,
            index_created_at=page.index_created_at,
        )
        write_json_once(
            path=output_dir / f"page_{offset:08d}.manifest.json", value=asdict(manifest)
        )
        page_manifests.append(manifest)
        page_hashes.append(response_hash)
        offset += len(page.records)
        if len(page.records) == 0:
            break
        save_checkpoint(
            path=checkpoint_path,
            checkpoint=DownloadCheckpoint(
                query_hash=identity,
                next_offset=offset,
                expected_total=expected_total,
                page_hashes=tuple(page_hashes),
            ),
        )
    if expected_total is None:
        raise DownloadValidationError("FDIC download did not return a total")
    records: list[Record] = assemble_saved_pages(
        output_dir=output_dir,
        requested_fields=frozenset(query.fields),
        required_fields=required_fields,
        allowed_unexpected_fields=allowed_unexpected_fields,
        expected_total=expected_total,
    )
    duplicates: list[tuple[str, str]] = find_duplicate_bank_quarters(records)
    if duplicates:
        raise DownloadValidationError(
            f"Duplicate bank-quarter records detected: count={len(duplicates)}, sample={duplicates[:10]}"
        )
    run_manifest: dict[str, object] = {
        "query_hash": identity,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total": expected_total,
        "page_count": len(
            [
                path
                for path in output_dir.glob("page_*.json")
                if not path.name.endswith(".manifest.json")
            ]
        ),
        "page_hashes": page_hashes,
    }
    run_manifest_path: Path = output_dir / "download_manifest.json"
    if not run_manifest_path.exists():
        write_json_once(path=run_manifest_path, value=run_manifest)
    return DownloadResult(
        records=records,
        pages=tuple(page_manifests),
        total=expected_total,
        query_hash=identity,
    )
