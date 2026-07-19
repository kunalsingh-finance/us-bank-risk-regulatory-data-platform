"""Inventory large and potentially sensitive objects in local Git history."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
LARGE_OBJECT_BYTES: int = 5 * 1024 * 1024
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
)


def git_output(arguments: list[str], input_text: str | None) -> str:
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *arguments], cwd=ROOT, input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    )
    return completed.stdout


def object_rows() -> list[dict[str, str | int]]:
    objects: list[tuple[str, str]] = []
    for line in git_output(["rev-list", "--objects", "--all"], None).splitlines():
        parts: list[str] = line.split(" ", 1)
        objects.append((parts[0], parts[1] if len(parts) == 2 else ""))
    batch_input: str = "".join(f"{identifier}\n" for identifier, _ in objects)
    metadata_lines: list[str] = git_output(["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"], batch_input).splitlines()
    paths: dict[str, str] = {identifier: path for identifier, path in objects}
    rows: list[dict[str, str | int]] = []
    for line in metadata_lines:
        identifier, object_type, size_text = line.split(" ", 2)
        size: int = int(size_text)
        if object_type == "blob" and size >= LARGE_OBJECT_BYTES:
            path: str = paths.get(identifier, "")
            rows.append({
                "check_type": "large_history_object", "object_id": identifier, "relative_path": path, "size_bytes": size,
                "status": "EXCLUDED_FROM_CLEAN_CANDIDATE", "detail": "Object remains in private development history; publish from the clean candidate with fresh history.",
            })
    return rows


def secret_rows() -> list[dict[str, str | int]]:
    patch: str = git_output(["log", "--all", "-p", "--format=commit %H", "--", ":(exclude)reports/*.csv"], None)
    rows: list[dict[str, str | int]] = []
    current_commit: str = ""
    for line in patch.splitlines():
        if line.startswith("commit "):
            current_commit = line.split(" ", 1)[1]
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                rows.append({
                    "check_type": "secret_pattern", "object_id": current_commit, "relative_path": "history_patch", "size_bytes": 0,
                    "status": "UNRESOLVED", "detail": name,
                })
    return rows


def remote_rows() -> list[dict[str, str | int]]:
    remotes: str = git_output(["remote", "-v"], None)
    credential_url: re.Pattern[str] = re.compile(r"https?://[^/\s:@]+:[^/\s@]+@")
    status: str = "PASS" if not credential_url.search(remotes) else "UNRESOLVED"
    return [{
        "check_type": "remote_credentials", "object_id": "", "relative_path": "git remotes", "size_bytes": 0,
        "status": status, "detail": "No credential-bearing remote URL detected." if status == "PASS" else "Credential-bearing remote URL detected; remove and rotate before publication.",
    }]


def main() -> None:
    rows: list[dict[str, str | int]] = [*remote_rows(), *secret_rows(), *object_rows()]
    output: Path = ROOT / "reports/git_history_safety_review.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=["check_type", "object_id", "relative_path", "size_bytes", "status", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    unresolved: int = sum(1 for row in rows if row["status"] == "UNRESOLVED")
    print(f"{'PASS' if unresolved == 0 else 'FAIL'}: history rows={len(rows)}, unresolved={unresolved}")
    if unresolved:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

