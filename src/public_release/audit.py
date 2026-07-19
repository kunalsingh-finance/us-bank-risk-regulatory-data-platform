"""Repository publication inventory and release-safety scans."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Final, Iterable

SKIPPED_DIRECTORY_NAMES: Final[frozenset[str]] = frozenset({".git", ".venv", ".venv_release", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"})
TEXT_SUFFIXES: Final[frozenset[str]] = frozenset({".csv", ".json", ".md", ".py", ".sql", ".toml", ".txt", ".yaml", ".yml", ".gitignore"})
SECRET_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("generic_secret_assignment", re.compile(r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
)
LOCAL_PATH_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("windows_user_path", re.compile(r"(?i)[A-Z]:[/\\]Users[/\\][^/\\\s]+")),
    ("onedrive_path", re.compile(r"(?i)[A-Z]:[/\\].*?OneDrive[/\\]")),
    ("downloads_path", re.compile(r"(?i)[A-Z]:[/\\].*?Downloads[/\\]")),
    ("unix_home_path", re.compile(r"/(?:home|Users)/[^/\s]+/")),
    ("temporary_path", re.compile(r"(?i)(?:[A-Z]:[/\\](?:Temp|TMP)[/\\]|/tmp/)")),
)
BINARY_SUFFIXES: Final[frozenset[str]] = frozenset({".duckdb", ".pkl", ".pickle", ".joblib", ".xlsx", ".xls", ".zip", ".png", ".jpg", ".jpeg", ".pdf", ".parquet"})


def sha256_file(path: Path) -> str:
    digest: hashlib._Hash = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative: Path = path.relative_to(root)
        if any(part in SKIPPED_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.is_file():
            files.append(path)
    return tuple(sorted(files, key=lambda value: value.as_posix().lower()))


def tracked_files(root: Path) -> frozenset[str]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return frozenset(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Makefile", "LICENSE", ".gitignore"}


def read_text_for_scan(path: Path) -> str:
    if not is_text_candidate(path) or path.stat().st_size > 10 * 1024 * 1024:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def purpose_for_path(relative: str) -> str:
    if relative.startswith("public_release/data/"):
        return "Publication-safe demonstration data"
    if relative.startswith("docs/") or relative.endswith(".md"):
        return "Research, governance, or usage documentation"
    if relative.startswith("sql/"):
        return "SQL-first transformation and control logic"
    if relative.startswith("src/") or relative.startswith("scripts/"):
        return "Reproducible application or orchestration source code"
    if relative.startswith("tests/"):
        return "Verification code"
    if relative.startswith("reports/"):
        return "Generated analytical or control report"
    if relative.startswith("data/raw/"):
        return "Locally acquired source data"
    if relative.startswith("database/"):
        return "Locally generated analytical database"
    if relative.startswith("artifacts/"):
        return "Locally generated model artifact"
    return "Repository support artifact"


def publication_decision(relative: str, tracked: bool) -> tuple[str, str, str, str]:
    public_authored: bool = relative.startswith((".github/", ".streamlit/", "configs/", "dashboards/", "docs/", "public_release/", "scripts/", "sql/", "src/", "tests/public_release/")) or relative in {
        ".gitignore", "CHANGELOG.md", "CONTRIBUTING.md", "COPYRIGHT_AND_LICENSE_REVIEW.md", "LICENSE", "Makefile",
        "PUBLICATION_INVENTORY.csv", "README.md", "RESPONSIBLE_USE.md", "SECURITY_AND_PRIVACY_SCAN.md",
        "THIRD_PARTY_NOTICES.md", "pyproject.toml", "requirements-dev.txt", "requirements.txt",
    }
    if ".egg-info/" in relative or relative.endswith(".egg-info"):
        return ("EXCLUDE_LOCAL_METADATA", "Dependency files", "UNTRACK", "Generated package metadata is reproducible and machine-specific.")
    if relative.startswith("data/raw/"):
        return ("EXCLUDE_RAW_DATA", "Official source-download workflow", "UNTRACK", "Redistribution rights were not established for copied raw files.")
    if relative.startswith("data/interim/") or relative.startswith("data/processed/") or relative.startswith("data/external/"):
        return ("EXCLUDE_GENERATED_BINARY", "Publication-safe synthetic package", "UNTRACK", "Full generated datasets are large and may expose institution-level records.")
    if relative.startswith("database/") or relative.startswith("artifacts/") or relative.startswith("results/"):
        return ("EXCLUDE_GENERATED_BINARY", "Reproducible build instructions and aggregate evidence", "UNTRACK", "Generated database and model binaries are intentionally local-only.")
    if relative.startswith("logs/") or relative.startswith(".streamlit/secrets"):
        return ("EXCLUDE_LOCAL_METADATA", "None", "UNTRACK", "Local runtime metadata is not a publication artifact.")
    if relative.startswith("reports/"):
        replacement: str = f"public_release/reports/{Path(relative).name}" if Path(relative).name in safe_aggregate_reports() else "Aggregate documentation or synthetic replacement"
        return ("INCLUDE_AGGREGATE_ONLY", replacement, "UNTRACK" if not relative.startswith("reports/public/") else "TRACK", "Only reviewed aggregate reports are eligible for the candidate.")
    if relative.startswith("public_release/"):
        return ("INCLUDE", relative, "TRACK", "Publication-safe package artifact.")
    if tracked or public_authored:
        return ("INCLUDE", relative, "TRACK", "Authored source, configuration, tests, or documentation subject to release scanning.")
    return ("MANUAL_REVIEW_REQUIRED", "None", "DO_NOT_TRACK", "Untracked artifact has not been approved for publication.")


def safe_aggregate_reports() -> frozenset[str]:
    return frozenset({
        "candidate_model_results.csv", "dashboard_chart_reconciliation.csv", "dashboard_data_reconciliation.csv",
        "dashboard_language_scan.csv", "locked_test_access_log.csv", "locked_test_metrics.csv", "model_feature_importance.csv",
        "model_performance_by_asset_band.csv", "model_performance_by_bank_class.csv", "model_performance_by_period.csv",
        "model_uncertainty_intervals.csv", "validation_model_comparison.csv",
    })


def build_publication_inventory(root: Path, output: Path) -> int:
    tracked: frozenset[str] = tracked_files(root)
    fields: tuple[str, ...] = (
        "relative_path", "file_type", "file_size_bytes", "sha256", "purpose", "source", "generated_or_authored",
        "contains_raw_data", "contains_model_output", "contains_personal_path", "contains_sensitive_metadata",
        "redistribution_status", "required_for_reproducibility", "required_for_demonstration", "publication_decision",
        "publication_replacement", "git_tracking_decision", "reason", "reviewer_status",
    )
    rows: list[dict[str, str | int]] = []
    for path in repository_files(root):
        relative: str = path.relative_to(root).as_posix()
        if path.resolve() == output.resolve():
            continue
        if relative in {"public_release/PUBLIC_RELEASE_QUALITY_GATE.json", "public_release/RELEASE_MANIFEST.json", "public_release/RELEASE_FILE_INVENTORY.csv"}:
            rows.append({
                "relative_path": relative, "file_type": path.suffix.lower(), "file_size_bytes": 0,
                "sha256": "SELF_REFERENTIAL_RELEASE_METADATA", "purpose": "Release manifest or candidate inventory", "source": "Project-generated",
                "generated_or_authored": "GENERATED", "contains_raw_data": "False", "contains_model_output": "False",
                "contains_personal_path": "False", "contains_sensitive_metadata": "False", "redistribution_status": "PROJECT_REVIEWED",
                "required_for_reproducibility": "False", "required_for_demonstration": "False", "publication_decision": "INCLUDE",
                "publication_replacement": relative, "git_tracking_decision": "TRACK",
                "reason": "Release metadata cannot transitively hash itself and the repository inventory.", "reviewer_status": "REVIEWED",
            })
            continue
        content: str = read_text_for_scan(path)
        personal: bool = relative != "src/public_release/audit.py" and any(pattern.search(content) for _, pattern in LOCAL_PATH_PATTERNS)
        sensitive: bool = any(pattern.search(content) for _, pattern in SECRET_PATTERNS)
        decision, replacement, tracking, reason = publication_decision(relative, relative in tracked)
        raw: bool = relative.startswith("data/raw/")
        model_output: bool = relative.startswith(("artifacts/", "results/")) or "model" in relative.lower() and relative.startswith("reports/")
        rows.append({
            "relative_path": relative, "file_type": path.suffix.lower() or path.name, "file_size_bytes": path.stat().st_size,
            "sha256": sha256_file(path), "purpose": purpose_for_path(relative), "source": "FDIC or generated" if raw else "Project-authored or generated",
            "generated_or_authored": "GENERATED" if relative.startswith(("data/", "database/", "artifacts/", "reports/", "manifests/", "logs/", "public_release/data/")) else "AUTHORED",
            "contains_raw_data": str(raw), "contains_model_output": str(model_output), "contains_personal_path": str(personal),
            "contains_sensitive_metadata": str(sensitive), "redistribution_status": "UNCERTAIN_EXCLUDE" if raw else "PROJECT_REVIEWED",
            "required_for_reproducibility": str(relative.startswith(("src/", "scripts/", "sql/", "configs/"))),
            "required_for_demonstration": str(relative.startswith(("dashboards/", "src/dashboard/", "public_release/"))),
            "publication_decision": decision, "publication_replacement": replacement, "git_tracking_decision": tracking,
            "reason": reason, "reviewer_status": "REVIEWED" if decision != "MANUAL_REVIEW_REQUIRED" else "OPEN",
        })
    rows.append({
        "relative_path": output.relative_to(root).as_posix(), "file_type": output.suffix.lower(), "file_size_bytes": 0,
        "sha256": "SELF_REFERENTIAL_NOT_HASHED", "purpose": "File-level publication decision inventory", "source": "Project-generated",
        "generated_or_authored": "GENERATED", "contains_raw_data": "False", "contains_model_output": "False",
        "contains_personal_path": "False", "contains_sensitive_metadata": "False", "redistribution_status": "PROJECT_REVIEWED",
        "required_for_reproducibility": "False", "required_for_demonstration": "False", "publication_decision": "INCLUDE",
        "publication_replacement": output.relative_to(root).as_posix(), "git_tracking_decision": "TRACK",
        "reason": "The inventory cannot hash itself; every other listed artifact has a SHA-256 digest.", "reviewer_status": "REVIEWED",
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def scan_patterns(root: Path, files: Iterable[Path], patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> list[dict[str, str | int]]:
    findings: list[dict[str, str | int]] = []
    for path in files:
        content: str = read_text_for_scan(path)
        for line_number, line in enumerate(content.splitlines(), start=1):
            for finding_type, pattern in patterns:
                if pattern.search(line):
                    findings.append({
                        "relative_path": path.relative_to(root).as_posix(), "line": line_number, "finding_type": finding_type,
                        "review_status": "UNRESOLVED", "evidence": line.strip()[:240],
                    })
    return findings


def write_scan_report(rows: list[dict[str, str | int]], output: Path) -> None:
    fields: tuple[str, ...] = ("relative_path", "line", "finding_type", "review_status", "evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
