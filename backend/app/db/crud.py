"""Database write helpers for background metric ingestion."""
from __future__ import annotations

import logging
from datetime import datetime
from time import monotonic

from sqlalchemy import insert
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import LiquidityMetric

logger = logging.getLogger(__name__)

# After a failed write, back off briefly so an unreachable database doesn't
# stall the real-time WebSocket stream on every single event.
_COOLDOWN_SECONDS = 30.0
_last_failure = 0.0


def save_metrics_to_db(
    *,
    pool_address: str,
    time: datetime,
    token_a_reserve: float | None,
    token_b_reserve: float | None,
    swap_volume: float,
    predicted_drain: float,
    predicted_price_impact: float,
    session: Session | None = None,
) -> None:
    """INSERT one `LiquidityMetric` row (best-effort; never raises).

    When called without an explicit `session` (the production path), a short
    cooldown suppresses repeated writes while the database is unreachable so
    the WebSocket stream keeps flowing in mock mode.
    """
    global _last_failure

    owns_session = session is None
    if owns_session and monotonic() - _last_failure < _COOLDOWN_SECONDS:
        return

    db = session if session is not None else SessionLocal()
    try:
        db.execute(
            insert(LiquidityMetric.__table__).values(
                time=time,
                pool_address=pool_address,
                token_a_reserve=token_a_reserve,
                token_b_reserve=token_b_reserve,
                swap_volume=swap_volume,
                predicted_drain=predicted_drain,
                predicted_price_impact=predicted_price_impact,
            )
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - ingestion must not crash the stream
        db.rollback()
        _last_failure = monotonic()
        logger.warning(
            "Failed to persist liquidity metric (backing off %.0fs): %s",
            _COOLDOWN_SECONDS,
            exc,
        )
    finally:
        if owns_session:
            db.close()
