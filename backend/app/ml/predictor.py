"""Drain predictor: XGBoost when available, transparent heuristic otherwise."""
from __future__ import annotations

import time

from ..core.config import Settings
from ..schemas.prediction import DrainPrediction
from .model import XGBDrainModel


class DrainPredictor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = XGBDrainModel(settings.model_path)
        self._model.load()

    def predict(
        self,
        *,
        features: list[float],
        liquidity_change_pct: float | None,
        price_impact_pct: float | None,
        pair: str,
        pool_address: str,
    ) -> DrainPrediction:
        if self._model.loaded:
            probability = self._model.predict_proba([features])[0]
            model_used = "xgboost"
        else:
            probability = self._heuristic(features, liquidity_change_pct, price_impact_pct)
            model_used = "heuristic"

        probability = min(max(probability, 0.0), 1.0)
        level = self._alert_level(probability)
        message = self._message(level, pair, liquidity_change_pct, price_impact_pct)

        return DrainPrediction(
            pool_address=pool_address,
            pair=pair,
            drain_probability=round(probability, 4),
            alert_level=level,
            liquidity_change_pct=liquidity_change_pct,
            price_impact_pct=price_impact_pct,
            message=message,
            model_used=model_used,
            timestamp=int(time.time()),
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _alert_level(probability: float) -> str:
        if probability >= 0.8:
            return "CRITICAL"
        if probability >= 0.6:
            return "HIGH"
        if probability >= 0.3:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _heuristic(
        features: list[float],
        liquidity_change_pct: float | None,
        price_impact_pct: float | None,
    ) -> float:
        """Transparent rule-based drain score (used when no model is trained).

        The score is built additively from domain heuristics, each bucket
        contributing a fixed weight, and is capped at 0.95 (never certain):
          - deeper liquidity drains        -> +0.50 / +0.35 / +0.15
          - larger reference price impact  -> +0.30 / +0.20 / +0.10
          - more pending mempool swaps     -> +0.10 / +0.05
          - elevated 5-minute volatility   -> +0.05
        Feature indices 4 and 7 reference `ml.features.FEATURE_NAMES`
        (pending_swaps and price_volatility_5m respectively).
        """
        # Feature order is defined in `ml.features.FEATURE_NAMES`.
        score = 0.0

        change = liquidity_change_pct if liquidity_change_pct is not None else 0.0
        if change <= -0.25:
            score += 0.50
        elif change <= -0.15:
            score += 0.35
        elif change <= -0.05:
            score += 0.15

        impact = abs(price_impact_pct) if price_impact_pct is not None else 0.0
        if impact >= 10.0:
            score += 0.30
        elif impact >= 5.0:
            score += 0.20
        elif impact >= 2.0:
            score += 0.10

        pending = features[4] if len(features) > 4 else 0.0
        if pending >= 20:
            score += 0.10
        elif pending >= 5:
            score += 0.05

        volatility = features[7] if len(features) > 7 else 0.0
        if volatility >= 0.05:
            score += 0.05

        return min(score, 0.95)

    @staticmethod
    def _message(
        level: str,
        pair: str,
        liquidity_change_pct: float | None,
        price_impact_pct: float | None,
    ) -> str:
        parts: list[str] = []
        if liquidity_change_pct is not None and liquidity_change_pct < 0:
            parts.append(
                f"{pair} pool is predicted to experience a "
                f"{abs(liquidity_change_pct) * 100:.1f}% liquidity drain"
            )
        if price_impact_pct is not None and price_impact_pct < 0:
            parts.append(f"{abs(price_impact_pct):.2f}% price impact on a $100k reference trade")
        if not parts:
            parts.append(f"{pair} pool is stable")
        prefix = "Warning: " if level in {"MEDIUM", "HIGH", "CRITICAL"} else ""
        return prefix + "; ".join(parts)
