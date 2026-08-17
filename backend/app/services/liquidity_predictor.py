"""Liquidity / price-impact ML inference service.

`LiquidityPredictor` is the ML entry point used by the real-time event stream.
It tries to load a serialized scikit-learn / XGBoost model (`.pkl`) and, when no
model is available, falls back to a transparent, deterministic mock inference so
the pipeline is always runnable.

The public `predict` method always returns the same JSON shape:

    {
        "predicted_drain_percentage": float,  # 0..100
        "predicted_price_impact": float,      # 0..100 (percent)
        "risk_level": "Low" | "Medium" | "High",
    }
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Gas price (in gwei) above which the mock model starts adding "congestion"
# pressure to the drain estimate.
_BASE_GAS_GWEI = 30.0


class LiquidityPredictor:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        self._model: Any = None
        if model_path:
            self._load_model(model_path)

    # ------------------------------------------------------------------ #
    # Model loading
    # ------------------------------------------------------------------ #
    def _load_model(self, model_path: str) -> None:
        if not os.path.exists(model_path):
            logger.info("No ML model at %s — using mock inference", model_path)
            return
        try:
            import joblib

            self._model = joblib.load(model_path)
            logger.info("Loaded ML model from %s", model_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load model %s: %s", model_path, exc)
            self._model = None

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def predict(
        self,
        *,
        swap_volume: float,
        reserve_depth: float,
        gas_price: float,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run inference and return the canonical JSON prediction structure.

        Args:
            swap_volume: traded notional (USD-equivalent units).
            reserve_depth: pool reserve depth (USD-equivalent units).
            gas_price: current gas price in wei.
            context: optional extra signal (e.g. event type).
        """
        if self._model is not None:
            try:
                return self._predict_with_model(swap_volume, reserve_depth, gas_price, context)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model inference failed (%s); using mock", exc)
        return self._mock_inference(swap_volume, reserve_depth, gas_price, context)

    # ------------------------------------------------------------------ #
    # Mock inference (deterministic stand-in for a trained model)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _mock_inference(
        swap_volume: float,
        reserve_depth: float,
        gas_price: float,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        volume = max(float(swap_volume), 0.0)
        depth = max(float(reserve_depth), 1.0)
        gas_gwei = max(float(gas_price), 0.0) / 1e9

        # Fraction of the pool's depth being traded.
        utilization = volume / depth

        # Linear slippage approximation for price impact (percent).
        predicted_price_impact = min(utilization * 100.0, 100.0)

        # Drain estimate: usage pressure + gas congestion + withdrawals.
        gas_pressure = max(0.0, (gas_gwei - _BASE_GAS_GWEI) / 300.0)
        drain = utilization * 100.0 * 0.6 + gas_pressure * 30.0
        if context and context.get("event") == "Burn":
            drain += 5.0  # liquidity withdrawal nudges the drain estimate up
        predicted_drain_percentage = min(drain, 100.0)

        return {
            "predicted_drain_percentage": round(predicted_drain_percentage, 4),
            "predicted_price_impact": round(predicted_price_impact, 4),
            "risk_level": LiquidityPredictor._risk_level(
                predicted_drain_percentage, predicted_price_impact
            ),
        }

    # ------------------------------------------------------------------ #
    # Trained-model inference (best-effort across common model shapes)
    # ------------------------------------------------------------------ #
    def _predict_with_model(
        self,
        swap_volume: float,
        reserve_depth: float,
        gas_price: float,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        import numpy as np

        features = np.asarray([[swap_volume, reserve_depth, gas_price]], dtype=float)

        try:
            # Regression model returning [drain_pct, impact_pct].
            output = self._model.predict(features)[0]
            drain = float(output[0])
            impact = float(output[1])
        except Exception:  # noqa: BLE001
            # Classifier model returning class probabilities.
            try:
                proba = self._model.predict_proba(features)[0]
                drain = float(proba[1]) * 100.0 if len(proba) > 1 else float(proba[0]) * 100.0
                impact = 0.0
            except Exception as exc:  # noqa: BLE001
                raise exc

        return {
            "predicted_drain_percentage": round(drain, 4),
            "predicted_price_impact": round(impact, 4),
            "risk_level": self._risk_level(drain, impact),
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def _risk_level(drain_pct: float, impact_pct: float) -> str:
        score = max(drain_pct, impact_pct)
        if score >= 20.0:
            return "High"
        if score >= 8.0:
            return "Medium"
        return "Low"
