"""Pure dashboard filter application."""

from __future__ import annotations

import pandas as pd


def filter_frame(frame: pd.DataFrame, selections: dict[str, tuple[object, ...]]) -> pd.DataFrame:
    result: pd.DataFrame = frame.copy()
    for column, values in selections.items():
        if values:
            result = result.loc[result[column].isin(values)]
    return result
