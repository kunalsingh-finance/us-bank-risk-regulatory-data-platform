"""Chronological split and expanding-window fold utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class DateWindow:
    name: str
    start: date
    end: date


def parse_window(name: str, values: list[object]) -> DateWindow:
    if len(values) != 2 or not all(isinstance(item, str) for item in values):
        raise ValueError(f"Invalid date window {name}: {values!r}")
    return DateWindow(name, date.fromisoformat(str(values[0])), date.fromisoformat(str(values[1])))


def assign_split(value: date, windows: tuple[DateWindow, ...]) -> str:
    matches: tuple[str, ...] = tuple(window.name for window in windows if window.start <= value <= window.end)
    if len(matches) > 1:
        raise ValueError(f"Date occurs in multiple splits: date={value}, splits={matches}")
    return matches[0] if matches else "OUTSIDE_PROTOCOL"


def frame_window(frame: pd.DataFrame, window: DateWindow) -> pd.DataFrame:
    dates: pd.Series = pd.to_datetime(frame["reporting_date"])
    return frame.loc[(dates >= pd.Timestamp(window.start)) & (dates <= pd.Timestamp(window.end))].copy()


def validate_order(windows: tuple[DateWindow, ...]) -> None:
    ordered: tuple[DateWindow, ...] = tuple(sorted(windows, key=lambda item: item.start))
    for prior, current in zip(ordered, ordered[1:], strict=False):
        if prior.end >= current.start:
            raise ValueError(f"Temporal splits overlap: {prior} and {current}")
