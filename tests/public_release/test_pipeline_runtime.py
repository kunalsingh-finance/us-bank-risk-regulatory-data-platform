"""Check interpreter continuity without executing the external research build."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("python_name", ["python", "python3"])
def test_rebuild_stage_uses_active_interpreter_without_path_python(tmp_path, python_name):
    marker = tmp_path / "interpreter.json"
    config = tmp_path / "pipeline.json"
    stage_code = (
        "import json, pathlib, sys; "
        "pathlib.Path(sys.argv[1]).write_text(json.dumps({'executable': sys.executable}), encoding='utf-8')"
    )
    config.write_text(json.dumps({"stages": [{"command": [python_name, "-c", stage_code, str(marker)]}]}), encoding="utf-8")
    environment = dict(os.environ, BANK_RISK_FULL_REBUILD_CONFIRM="YES", PATH=str(tmp_path))
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_full_pipeline.py"), "--config", str(config)],
        cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["executed_stages"] == 1
    observed = json.loads(marker.read_text(encoding="utf-8"))
    assert Path(observed["executable"]).resolve() == Path(sys.executable).resolve()
