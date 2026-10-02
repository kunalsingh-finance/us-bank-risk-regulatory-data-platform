"""Validate and, when explicitly authorized, execute the full logical rebuild plan."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]


def parse_arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Run the configured full research pipeline.")
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Full-pipeline configuration must use JSON-compatible YAML: path={path}, error={error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Full-pipeline configuration must be an object: path={path}")
    return value


def stage_commands(config: dict[str, object]) -> tuple[tuple[str, ...], ...]:
    raw_stages: object = config.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise ValueError("Full-pipeline configuration requires a non-empty stages list.")
    commands: list[tuple[str, ...]] = []
    for raw_stage in raw_stages:
        if not isinstance(raw_stage, dict) or not isinstance(raw_stage.get("command"), list):
            raise ValueError(f"Every pipeline stage requires a command list: stage={raw_stage}")
        command: tuple[str, ...] = tuple(str(value) for value in raw_stage["command"])
        if not command:
            raise ValueError(f"Pipeline stage command cannot be empty: stage={raw_stage}")
        if command[0] in {"python", "python3"}:
            command = (sys.executable, *command[1:])
        commands.append(command)
    return tuple(commands)


def main() -> None:
    arguments: argparse.Namespace = parse_arguments()
    config_path: Path = arguments.config if arguments.config.is_absolute() else ROOT / arguments.config
    config: dict[str, object] = load_config(config_path)
    commands: tuple[tuple[str, ...], ...] = stage_commands(config)
    if os.environ.get("BANK_RISK_FULL_REBUILD_CONFIRM", "") != "YES":
        print(json.dumps({"status": "PLAN_VALIDATED", "stages": [list(value) for value in commands], "execution": "Set BANK_RISK_FULL_REBUILD_CONFIRM=YES to execute."}, indent=2))
        return
    for command in commands:
        completed: subprocess.CompletedProcess[bytes] = subprocess.run(list(command), cwd=ROOT, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"Full-pipeline stage failed: command={list(command)}, returncode={completed.returncode}")
    print(json.dumps({"status": "PASS", "executed_stages": len(commands)}, sort_keys=True))


if __name__ == "__main__":
    main()

