"""Streamlit entry point for the bank-risk dashboard."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.app_pages import render_executive  # noqa: E402


render_executive()
