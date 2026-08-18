"""Feature engineering: target construction and aligned feature matrix."""
from __future__ import annotations

import pandas as pd

from config import FEATURE_COLUMNS, TARGET_TYPE


def build_dataset(
    raw: pd.DataFrame, target_type: str = TARGET_TYPE
) -> tuple[pd.DataFrame, list[str]]:
    """Return (dataset, feature_columns) with the target label appended.

    Target:
      - regression     -> next day's closing price
      - classification -> 1 if next day's close is above today's close, else 0

    `raw` is expected to be the aligned, forward-filled frame from
    `data_source.fetch_all`.
    """
    df = raw.copy().sort_index()

    # Next-day close (shift -1: today's row predicts tomorrow).
    df["target_close"] = df["close"].shift(-1)

    if target_type == "classification":
        df["target"] = (df["target_close"] > df["close"]).astype(int)
    else:
        df["target"] = df["target_close"]

    features = list(FEATURE_COLUMNS)

    # Keep only complete rows (no target tomorrow, and no missing features).
    df = df.dropna(subset=features + ["target"]).copy()
    return df, features
