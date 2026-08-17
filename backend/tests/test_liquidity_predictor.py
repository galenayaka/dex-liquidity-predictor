"""Unit tests for LiquidityPredictor (mock inference path)."""
from __future__ import annotations

from app.services.liquidity_predictor import LiquidityPredictor


def test_mock_inference_returns_expected_shape():
    predictor = LiquidityPredictor()  # no model file -> mock inference
    result = predictor.predict(
        swap_volume=100_000.0,
        reserve_depth=58_000_000.0,
        gas_price=30 * 10**9,
    )
    assert set(result) == {
        "predicted_drain_percentage",
        "predicted_price_impact",
        "risk_level",
    }
    assert 0.0 <= result["predicted_drain_percentage"] <= 100.0
    assert 0.0 <= result["predicted_price_impact"] <= 100.0
    assert result["risk_level"] in {"Low", "Medium", "High"}


def test_larger_trade_has_higher_risk():
    predictor = LiquidityPredictor()
    small = predictor.predict(
        swap_volume=1_000.0, reserve_depth=58_000_000.0, gas_price=30 * 10**9
    )
    large = predictor.predict(
        swap_volume=30_000_000.0, reserve_depth=58_000_000.0, gas_price=30 * 10**9
    )
    assert large["predicted_price_impact"] > small["predicted_price_impact"]
    assert large["risk_level"] != "Low"


def test_burn_event_boosts_drain_estimate():
    predictor = LiquidityPredictor()
    swap = predictor.predict(
        swap_volume=1_000_000.0,
        reserve_depth=58_000_000.0,
        gas_price=30 * 10**9,
        context={"event": "Swap"},
    )
    burn = predictor.predict(
        swap_volume=1_000_000.0,
        reserve_depth=58_000_000.0,
        gas_price=30 * 10**9,
        context={"event": "Burn"},
    )
    assert burn["predicted_drain_percentage"] > swap["predicted_drain_percentage"]
