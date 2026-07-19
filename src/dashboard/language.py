"""Context-aware scan for misleading dashboard language."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROHIBITED_PHRASES: tuple[str, ...] = (
    "probability of failure", "failure probability", "probability of default", "will fail",
    "likely to fail", "official camels", "regulatory rating", "safe bank", "unsafe bank",
    "guaranteed", "predicts failure with certainty", "investment recommendation",
)
NEGATION_MARKERS: tuple[str, ...] = (" not ", " no ", "does not", "do not", "never", "prohibited", "excluded", "must not", "cannot", "isn't", "aren't")


def scan_text(path: Path, text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        normalized: str = f" {line.lower()} "
        for phrase in PROHIBITED_PHRASES:
            if phrase in normalized:
                control_definition: bool = path.name == "language.py"
                allowed: bool = control_definition or any(marker in normalized for marker in NEGATION_MARKERS) or "prohibited_wording" in normalized
                findings.append({"file": path.as_posix(), "line": number, "phrase": phrase, "context": line.strip(),
                                 "status": "ALLOWED_CONTROL_DEFINITION" if control_definition else "ALLOWED_NEGATED_EXPLANATION" if allowed else "UNRESOLVED_MISLEADING_LANGUAGE"})
    return findings


def scan_paths(root: Path, paths: tuple[Path, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in paths:
        rows.extend(scan_text(path.relative_to(root), path.read_text(encoding="utf-8")))
    if not rows:
        return pd.DataFrame([{"file": "ALL_SCANNED_FILES", "line": 0, "phrase": "", "context": "No prohibited phrase found", "status": "PASS"}])
    return pd.DataFrame(rows).sort_values(["status", "file", "line"]).reset_index(drop=True)
