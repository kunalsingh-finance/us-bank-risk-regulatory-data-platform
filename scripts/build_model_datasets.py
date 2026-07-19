"""Build split-assigned model datasets without exposing locked-test targets."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from src.models.dataset import DatasetBuildResult,build_model_datasets  # noqa: E402


def main() -> None:
    result: DatasetBuildResult = build_model_datasets(ROOT)
    print(f"PASS database={result.database_path} sha256={result.database_sha256}")
    print(f"PASS features={result.feature_count} split_sha256={result.split_assignment_sha256}")


if __name__ == "__main__":
    main()
