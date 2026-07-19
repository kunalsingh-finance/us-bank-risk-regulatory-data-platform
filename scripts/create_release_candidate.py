"""Copy only explicitly approved public files into a clean release directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
PUBLIC_DIRECTORIES: tuple[str, ...] = (".github", ".streamlit", "configs", "dashboards", "docs", "public_release", "scripts", "sql", "src", "tests/public_release")
PUBLIC_TOP_LEVEL_FILES: tuple[str, ...] = (
    ".gitignore", "CHANGELOG.md", "CONTRIBUTING.md", "COPYRIGHT_AND_LICENSE_REVIEW.md", "LICENSE", "Makefile",
    "PUBLICATION_INVENTORY.csv", "README.md", "RESPONSIBLE_USE.md", "SECURITY_AND_PRIVACY_SCAN.md", "THIRD_PARTY_NOTICES.md",
    "pyproject.toml", "requirements-dev.txt", "requirements.txt",
)
PUBLIC_MANIFESTS: tuple[str, ...] = (
    "manifests/model_experiment/protocol_manifest.json",
    "manifests/model_experiment/pre_test_selection_manifest.json",
    "manifests/dashboard_build/run_manifest.json",
)


def parse_arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Create a clean public release candidate.")
    parser.add_argument("--destination", type=Path, required=True)
    return parser.parse_args()


def copy_path(source: Path, destination: Path) -> None:
    if source.is_dir() and source.name == "scripts":
        destination.mkdir(parents=True)
        for child in source.iterdir():
            if child.is_file():
                shutil.copy2(child, destination / child.name)
    elif source.is_dir():
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.egg-info",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "MODEL_CARD_DRAFT.md",
                "MODEL_VALIDATION_REPORT_DRAFT.md",
            ),
        )
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    else:
        raise FileNotFoundError(f"Approved public artifact is missing: {source}")


def main() -> None:
    arguments: argparse.Namespace = parse_arguments()
    destination: Path = arguments.destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Release candidate destination already exists; refusing to overwrite: {destination}")
    destination.mkdir(parents=True)
    for relative in PUBLIC_DIRECTORIES:
        copy_path(ROOT / relative, destination / relative)
    for relative in PUBLIC_TOP_LEVEL_FILES:
        copy_path(ROOT / relative, destination / relative)
    for relative in PUBLIC_MANIFESTS:
        copy_path(ROOT / relative, destination / relative)
    (destination / ".public-release-candidate").write_text("Publication-safe clean candidate; generated from an explicit allowlist.\n", encoding="utf-8")
    print(f"PASS: clean release candidate created at {destination}")


if __name__ == "__main__":
    main()
