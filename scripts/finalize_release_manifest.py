"""Create deterministic file inventory and manifest for a clean candidate."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.public_release.audit import repository_files, sha256_file  # noqa: E402

SELF_REFERENTIAL: frozenset[str] = frozenset({"public_release/RELEASE_MANIFEST.json", "public_release/RELEASE_FILE_INVENTORY.csv"})


def parse_arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Finalize a clean public release manifest.")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--source-commit", type=str, required=True)
    parser.add_argument("--source-branch", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    arguments: argparse.Namespace = parse_arguments()
    candidate: Path = arguments.candidate.resolve()
    release_directory: Path = candidate / "public_release"
    rows: list[dict[str, str | int]] = []
    for path in repository_files(candidate):
        relative: str = path.relative_to(candidate).as_posix()
        if relative in SELF_REFERENTIAL:
            continue
        rows.append({"relative_path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path), "category": relative.split("/", 1)[0]})
    inventory_path: Path = release_directory / "RELEASE_FILE_INVENTORY.csv"
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=["relative_path", "size_bytes", "sha256", "category"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    quality_path: Path = release_directory / "PUBLIC_RELEASE_QUALITY_GATE.json"
    quality: dict[str, object] = json.loads(quality_path.read_text(encoding="utf-8"))
    manifest: dict[str, object] = {
        "release_candidate_version": "1.0.0-rc1", "source_commit": arguments.source_commit, "source_branch": arguments.source_branch,
        "file_count_excluding_self_referential_manifests": len(rows), "total_bytes_excluding_self_referential_manifests": sum(int(row["size_bytes"]) for row in rows),
        "release_inventory_sha256": sha256_file(inventory_path), "included_code": True, "included_documentation": True,
        "included_samples": "deterministic synthetic institution records and frozen aggregate validation evidence",
        "excluded_datasets": ["copied FDIC raw files", "full 698804-row panel", "full peer benchmark table", "institution-level prediction tables"],
        "excluded_model_artifacts": ["serialized selected model", "all model-development binaries"],
        "public_quality_gate": quality["status"], "clean_candidate_required": True,
        "remaining_restrictions": ["do not publish development Git history", "do not interpret ranks as probabilities", "do not deploy without a separate approval"],
        "publication_verdict": "RELEASE CANDIDATE ONLY — MANUAL PUBLICATION APPROVAL REQUIRED",
    }
    (release_directory / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "file_count": len(rows), "total_bytes": manifest["total_bytes_excluding_self_referential_manifests"]}, sort_keys=True))


if __name__ == "__main__":
    main()

