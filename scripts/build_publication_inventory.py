"""Build the file-level repository publication inventory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.public_release.audit import build_publication_inventory  # noqa: E402


def main() -> None:
    count: int = build_publication_inventory(ROOT, ROOT / "PUBLICATION_INVENTORY.csv")
    print(f"PASS: inventoried {count} repository artifacts")


if __name__ == "__main__":
    main()

