"""Run release-safety checks against the intended public candidate."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.public_release.audit import (  # noqa: E402
    BINARY_SUFFIXES,
    LOCAL_PATH_PATTERNS,
    SECRET_PATTERNS,
    read_text_for_scan,
    repository_files,
    scan_patterns,
    write_scan_report,
)
from src.public_release.validation import validate_demo_package  # noqa: E402

ALLOWED_BINARY_PATHS: tuple[str, ...] = ("public_release/data/",)
PROHIBITED_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("predicts_bank_failure", re.compile(r"(?i)\bpredicts? bank failure\b")),
    ("precision_misstatement", re.compile(r"(?i)\b14\.8% precision\b")),
    ("accuracy_multiplier", re.compile(r"(?i)\b289(?:\.3)?[x×]\s+more accurate\b")),
    ("failure_probability", re.compile(r"(?i)\bfailure probability\b")),
    ("will_fail", re.compile(r"(?i)\bwill fail\b")),
    ("likely_to_fail", re.compile(r"(?i)\blikely to fail\b")),
    ("official_camels", re.compile(r"(?i)\bofficial CAMELS\b")),
    ("regulatory_grade", re.compile(r"(?i)\bregulatory[- ]grade\b")),
    ("guaranteed", re.compile(r"(?i)\bguaranteed\b")),
    ("investment_signal", re.compile(r"(?i)\binvestment signal\b")),
    ("proven_alpha", re.compile(r"(?i)\bproven alpha\b")),
)
NEGATION_TERMS: tuple[str, ...] = ("not ", "no ", "never ", "must not", "do not", "does not", "cannot", "prohibited", "avoid", "isn't", "excluded", "claim made", "negated")


def parse_arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Run the public release quality gate.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def candidate_files(root: Path) -> tuple[Path, ...]:
    excluded_prefixes: tuple[str, ...] = (".git/", ".venv/", "data/", "database/", "artifacts/", "logs/", "results/", "reports/")
    return tuple(
        path for path in repository_files(root)
        if not path.relative_to(root).as_posix().startswith(excluded_prefixes)
        or path.relative_to(root).as_posix().startswith("public_release/")
    )


def claims_findings(root: Path, files: tuple[Path, ...]) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for path in files:
        content: str = read_text_for_scan(path)
        for line_number, line in enumerate(content.splitlines(), start=1):
            lowered: str = line.lower()
            for finding_type, pattern in PROHIBITED_CLAIM_PATTERNS:
                if pattern.search(line):
                    scanner_source: bool = path.name in {"language.py", "run_public_quality_gate.py"} or (path.name == "dashboard_language_scan.csv" and "ALLOWED_CONTROL_DEFINITION" in line)
                    governance_list: bool = "production supervision" in lowered and "investment advice" in lowered
                    resolved: bool = any(term in lowered for term in NEGATION_TERMS) or scanner_source or governance_list
                    rows.append({
                        "relative_path": path.relative_to(root).as_posix(), "line": line_number, "finding_type": finding_type,
                        "review_status": "RESOLVED_GOVERNANCE_CONTEXT" if resolved else "UNRESOLVED",
                        "evidence": line.strip()[:240],
                    })
    return rows


def binary_violations(root: Path, files: tuple[Path, ...]) -> list[str]:
    violations: list[str] = []
    for path in files:
        relative: str = path.relative_to(root).as_posix()
        if path.suffix.lower() in BINARY_SUFFIXES and not relative.startswith(ALLOWED_BINARY_PATHS):
            violations.append(relative)
    return sorted(violations)


def write_quality_checks(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=["check_id", "status", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    arguments: argparse.Namespace = parse_arguments()
    root: Path = arguments.root.resolve()
    output: Path = arguments.output if arguments.output.is_absolute() else root / arguments.output
    files: tuple[Path, ...] = candidate_files(root)
    secret_rows: list[dict[str, str | int]] = [row for row in scan_patterns(root, files, SECRET_PATTERNS) if row["relative_path"] != "src/public_release/audit.py"]
    path_rows: list[dict[str, str | int]] = [row for row in scan_patterns(root, files, LOCAL_PATH_PATTERNS) if row["relative_path"] != "src/public_release/audit.py"]
    claim_rows: list[dict[str, str | int]] = claims_findings(root, files)
    binaries: list[str] = binary_violations(root, files)
    reports: Path = root / "reports"
    write_scan_report(secret_rows, reports / "public_release_secret_scan.csv")
    write_scan_report(path_rows, reports / "public_release_local_path_scan.csv")
    write_scan_report(claim_rows, reports / "public_claims_audit.csv")
    metadata_rows: list[dict[str, str | int]] = [
        {"relative_path": value, "line": 0, "finding_type": "unsupported_binary", "review_status": "UNRESOLVED", "evidence": value}
        for value in binaries
    ]
    write_scan_report(metadata_rows, reports / "public_release_metadata_scan.csv")
    demo: dict[str, object] = validate_demo_package(root / "public_release/data")
    is_clean_candidate: bool = (root / ".public-release-candidate").exists()
    raw_present: bool = is_clean_candidate and (root / "data/raw").exists()
    model_binary_present: bool = is_clean_candidate and (root / "artifacts").exists()
    unresolved_claims: int = sum(1 for row in claim_rows if row["review_status"] == "UNRESOLVED")
    checks: list[dict[str, str]] = [
        {"check_id": "demo_package", "status": "PASS", "detail": f"{demo['score_rows']} synthetic score rows and {demo['frozen_metrics']} frozen metrics validated"},
        {"check_id": "secret_scan", "status": "PASS" if not secret_rows else "FAIL", "detail": f"findings={len(secret_rows)}"},
        {"check_id": "local_path_scan", "status": "PASS" if not path_rows else "FAIL", "detail": f"findings={len(path_rows)}"},
        {"check_id": "claims_audit", "status": "PASS" if unresolved_claims == 0 else "FAIL", "detail": f"unresolved={unresolved_claims}, reviewed_contexts={len(claim_rows) - unresolved_claims}"},
        {"check_id": "binary_policy", "status": "PASS" if not binaries else "FAIL", "detail": f"violations={len(binaries)}"},
        {"check_id": "clean_candidate_raw_exclusion", "status": "PASS" if not raw_present else "FAIL", "detail": f"clean_candidate={is_clean_candidate}, raw_present={raw_present}"},
        {"check_id": "clean_candidate_model_binary_exclusion", "status": "PASS" if not model_binary_present else "FAIL", "detail": f"clean_candidate={is_clean_candidate}, model_directory_present={model_binary_present}"},
        {"check_id": "responsible_use", "status": "PASS" if (root / "RESPONSIBLE_USE.md").exists() else "FAIL", "detail": "required policy file"},
        {"check_id": "license_boundary", "status": "PASS" if (root / "LICENSE").exists() and (root / "THIRD_PARTY_NOTICES.md").exists() else "FAIL", "detail": "code and third-party boundaries"},
    ]
    write_quality_checks(checks, reports / "public_release_quality_checks.csv")
    failed: list[str] = [row["check_id"] for row in checks if row["status"] != "PASS"]
    payload: dict[str, object] = {
        "version": "phase7-public-quality-gate-v1", "status": "PASS" if not failed else "FAIL", "candidate_files_scanned": len(files),
        "checks": checks, "failed_checks": failed, "demo_validation": demo,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "failed_checks": failed, "output": output.as_posix()}, sort_keys=True))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
