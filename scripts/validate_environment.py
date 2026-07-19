"""Validate the public demonstration runtime and its governed data contract."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.public_release.validation import validate_demo_package  # noqa: E402

REQUIRED_DISTRIBUTIONS: tuple[str, ...] = ("duckdb", "pandas", "pyarrow", "scikit-learn", "scipy", "streamlit", "plotly")


def installed_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in REQUIRED_DISTRIBUTIONS:
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(f"Required distribution is not installed: {distribution}") from error
    return versions


def main() -> None:
    if sys.version_info < (3, 11):
        raise RuntimeError(f"Python 3.11 or newer is required: observed={platform.python_version()}")
    validation: dict[str, object] = validate_demo_package(ROOT / "public_release/data")
    print(json.dumps({"status": "PASS", "python": platform.python_version(), "dependencies": installed_versions(), "demo": validation}, sort_keys=True))


if __name__ == "__main__":
    main()

