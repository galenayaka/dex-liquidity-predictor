"""Market-maker execution-layer endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ...core.container import get_market_maker_bot
from ...schemas.market_maker import MarketMakerStatus

router = APIRouter(prefix="/market-maker", tags=["market-maker"])


@router.get("/status", response_model=MarketMakerStatus)
def status() -> MarketMakerStatus:
    """Return the bot's current position state (simulated by default)."""
    return get_market_maker_bot().state()
