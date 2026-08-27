"""Historical liquidity metric endpoints."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...core.container import get_store
from ...db.database import get_db
from ...db.models import LiquidityMetric

router = APIRouter(prefix="/metrics", tags=["metrics"])

TimeRange = Literal["1h", "24h", "7d"]

_TIME_RANGES: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


class MetricPoint(BaseModel):
    """A single chart point directly consumable by `lightweight-charts`."""

    time: int  # unix timestamp (seconds)
    value: float  # token A reserve (USD-equivalent liquidity)


def _to_unix(dt: datetime) -> int:
    """Convert a (possibly naive) datetime to unix seconds."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


@router.get("/{pool_address}", response_model=list[MetricPoint])
def get_metrics(
    pool_address: str,
    time_range: TimeRange | None = None,
    db: Session = Depends(get_db),
) -> list[MetricPoint]:
    """Return the latest liquidity points for a pool, oldest first.

    Queries `liquidity_metrics` ordered by `time` descending and takes the
    most recent 100 rows, then reverses them so the response is ascending —
    the order `lightweight-charts` requires. `time_range` limits results to
    the last 1h / 24h / 7d.

    When no persisted rows exist (mock mode, fresh install, or the database is
    offline) the endpoint falls back to the in-memory snapshot history so the
    dashboard keeps working end-to-end without MySQL.
    """
    query = select(LiquidityMetric).where(
        func.lower(LiquidityMetric.pool_address) == pool_address.lower()
    )

    if time_range is not None:
        cutoff = datetime.now(timezone.utc) - _TIME_RANGES[time_range]
        query = query.where(LiquidityMetric.time >= cutoff)

    rows: list[LiquidityMetric] = []
    try:
        rows = list(
            db.scalars(
                query.order_by(LiquidityMetric.time.desc()).limit(100)
            ).all()
        )
    except SQLAlchemyError:
        rows = []

    if rows:
        return [
            MetricPoint(time=_to_unix(row.time), value=row.token_a_reserve)
            for row in reversed(rows)  # charts expect ascending time
            if row.token_a_reserve is not None
        ]

    # Fallback: serve the live in-memory snapshot history.
    snapshots = get_store().history(pool_address, limit=120)
    if time_range is not None:
        cutoff_ts = time.time() - _TIME_RANGES[time_range].total_seconds()
        snapshots = [
            s for s in snapshots
            if s.pool.timestamp is not None and s.pool.timestamp >= cutoff_ts
        ]

    points: list[MetricPoint] = []
    for snap in snapshots:
        if snap.pool.tvl_usd is None or snap.pool.timestamp is None:
            continue
        # `tvl_usd` covers both pool sides; a single reserve is ~half of it.
        points.append(
            MetricPoint(time=snap.pool.timestamp, value=snap.pool.tvl_usd / 2.0)
        )
    return points
