"""Shared / cross-cutting Pydantic models."""
from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    chain_id: int
    mock_mode: bool
    web3_connected: bool


class Alert(BaseModel):
    """Real-time warning pushed over the WebSocket channel."""

    type: str = "alert"
    level: str  # LOW | MEDIUM | HIGH | CRITICAL
    pool_address: str
    pair: str
    message: str
    drain_probability: float | None = None
    liquidity_change_pct: float | None = None
    price_impact_pct: float | None = None
    timestamp: int
