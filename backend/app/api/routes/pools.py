"""Pool snapshot & price-impact endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.config import get_settings
from ...core.exceptions import NotFoundError, PriceImpactError
from ...schemas.pool import PoolState
from ...schemas.prediction import PriceImpactRequest, PriceImpactResponse
from ..deps import (
    get_pool_provider,
    get_price_impact_service,
    get_store,
    rate_limit_dependency,
)

router = APIRouter(prefix="/pools", tags=["pools"])


def _resolve_pool(address: str) -> PoolState:
    """Return a live pool state, falling back to an on-demand fetch."""
    snapshot = get_store().latest(address)
    if snapshot is not None:
        return snapshot.pool

    settings = get_settings()
    entry = next(
        (e for e in settings.watchlist if e["address"].lower() == address.lower()),
        None,
    )
    if entry is None:
        raise NotFoundError(f"No pool watched at address {address}")
    return get_pool_provider().get_pool_state(entry)


@router.get("")
def list_pools() -> dict:
    snapshots = get_store().all_latest()
    return {"count": len(snapshots), "pools": [s.pool.model_dump() for s in snapshots]}


@router.get("/{address}")
def get_pool(address: str):
    snapshot = get_store().latest(address)
    if snapshot is None:
        raise NotFoundError(f"No snapshot for pool {address}")
    return snapshot


@router.get("/{address}/history")
def get_history(address: str, limit: int = Query(100, ge=1, le=2000)):
    return {"pool": address, "history": get_store().history(address, limit)}


@router.post(
    "/{address}/price-impact",
    response_model=PriceImpactResponse,
    dependencies=[Depends(rate_limit_dependency)],
)
def price_impact(address: str, body: PriceImpactRequest):
    pool = _resolve_pool(address)
    try:
        quote = get_price_impact_service().quote(pool, body.token_in, body.amount_in)
    except ValueError as exc:
        raise PriceImpactError(str(exc)) from exc
    return PriceImpactResponse(
        pool_address=pool.address,
        token_in=quote.token_in,
        token_out=quote.token_out,
        amount_in=quote.amount_in,
        amount_out=quote.amount_out,
        price_before=quote.price_before,
        price_after=quote.price_after,
        price_impact_pct=quote.price_impact_pct,
    )
