"""Feature engineering for the liquidity-drain classifier.

The feature order is FIXED and shared by the training script and the live
predictor. Do not reorder without retraining the model.
"""
from __future__ import annotations

import math

FEATURE_NAMES = [
    "liquidity_change_pct_1m",
    "liquidity_change_pct_5m",
    "liquidity_change_pct_15m",
    "reference_impact_pct",
    "pending_swaps",
    "fee_tier",
    "log_liquidity",
    "price_volatility_5m",
]


def build_feature_vector(
    *,
    liquidity_change_1m: float | None = 0.0,
    liquidity_change_5m: float | None = 0.0,
    liquidity_change_15m: float | None = 0.0,
    reference_impact_pct: float | None = 0.0,
    pending_swaps: int = 0,
    fee_tier: int = 0,
    liquidity: int = 0,
    price_volatility_5m: float | None = 0.0,
) -> list[float]:
    return [
        float(liquidity_change_1m or 0.0),
        float(liquidity_change_5m or 0.0),
        float(liquidity_change_15m or 0.0),
        float(reference_impact_pct or 0.0),
        float(pending_swaps),
        float(fee_tier),
        math.log10(liquidity) if liquidity and liquidity > 0 else 0.0,
        float(price_volatility_5m or 0.0),
    ]
