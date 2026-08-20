"""Pydantic models for the market-maker execution layer."""
from __future__ import annotations

from pydantic import BaseModel


class MarketMakerStatus(BaseModel):
    """Current state of the simulated (or real) liquidity position."""

    has_active_position: bool
    tick_lower: int
    tick_upper: int
    liquidity: int
    token_id: int | None = None
    simulation_mode: bool
    tick_spacing: int
