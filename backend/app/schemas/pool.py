"""Pydantic models for pools and liquidity snapshots."""
from __future__ import annotations

from pydantic import BaseModel


class TokenMeta(BaseModel):
    address: str
    symbol: str
    decimals: int


class PoolState(BaseModel):
    """On-chain state of a Uniswap v3 pool at a point in time."""

    address: str
    token0: TokenMeta
    token1: TokenMeta
    fee: int  # fee tier in hundredths of a bip (e.g. 3000 -> 0.3%)
    liquidity: int  # current in-range liquidity (Q128)
    sqrt_price_x96: int  # Q64.96 encoded sqrt price
    tick: int
    price: float  # human price of token0 denominated in token1
    tvl_usd: float | None = None
    timestamp: int | None = None


class PoolSnapshot(BaseModel):
    """A pool state plus derived analytics computed by the monitor."""

    pool: PoolState
    liquidity_change_pct_1m: float | None = None
    liquidity_change_pct_5m: float | None = None
    liquidity_change_pct_15m: float | None = None
    pending_swaps_1m: int = 0
    reference_impact_pct: float | None = None  # price impact of a $100k reference trade
