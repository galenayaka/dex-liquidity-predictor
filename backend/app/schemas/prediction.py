"""Pydantic models for price-impact quotes and drain predictions."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PriceImpactRequest(BaseModel):
    token_in: str = Field(..., description="Address of the input token")
    amount_in: float = Field(..., gt=0, description="Input amount in human-readable units")


class PriceImpactResponse(BaseModel):
    pool_address: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_before: float
    price_after: float
    price_impact_pct: float  # negative => price moved against the trader


class DrainPrediction(BaseModel):
    pool_address: str
    pair: str
    drain_probability: float  # 0..1
    alert_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    liquidity_change_pct: float | None = None
    price_impact_pct: float | None = None
    message: str
    model_used: str  # "xgboost" | "heuristic"
    timestamp: int


class PredictionResponse(BaseModel):
    prediction: DrainPrediction
