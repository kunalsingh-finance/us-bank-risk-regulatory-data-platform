"""Peer Comparison page."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.app_pages import render_peer_comparison  # noqa: E402

render_peer_comparison()
