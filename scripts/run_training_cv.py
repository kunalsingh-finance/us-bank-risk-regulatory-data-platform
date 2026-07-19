"""Run governed expanding-window CV and validation-only selection."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from src.models.trainer import develop_models  # noqa: E402


def main() -> None:
    selection = develop_models(ROOT)
    print(f"PASS selected_model={selection['selected_primary_model']} calibration={selection['selected_calibration_method']}")


if __name__ == "__main__":
    main()
