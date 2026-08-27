"""Background monitoring loop.

Periodically samples every watched pool, computes liquidity-change and
price-impact analytics, runs the drain predictor and broadcasts alerts over
the WebSocket channel.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
import time

from ..core.config import get_settings
from ..core.container import (
    get_market_maker_bot,
    get_mempool_watcher,
    get_pool_provider,
    get_predictor,
    get_price_impact_service,
    get_store,
    get_ws_manager,
)
from ..ml.features import build_feature_vector
from ..schemas.common import Alert
from ..schemas.pool import PoolSnapshot

logger = logging.getLogger(__name__)

_REFERENCE_TRADE_USD = 100_000.0


def _pct_change(history: list[PoolSnapshot], seconds_ago: int, current_liquidity: int) -> float | None:
    """Relative liquidity change vs the snapshot from `seconds_ago`.

    Walks the history backwards to find the newest snapshot at or before
    `now - seconds_ago`. If none is old enough, it falls back to the oldest
    available snapshot so short histories still produce a number. Returns
    None when there is no baseline or the baseline liquidity is zero.
    """
    cutoff = time.time() - seconds_ago
    baseline: PoolSnapshot | None = None
    for snap in reversed(history):
        ts = snap.pool.timestamp
        if ts is not None and ts <= cutoff:
            baseline = snap
            break
    if baseline is None and history:
        baseline = history[0]
    if baseline is None or baseline.pool.liquidity == 0:
        return None
    return (current_liquidity - baseline.pool.liquidity) / baseline.pool.liquidity


def _volatility(history: list[PoolSnapshot]) -> float:
    """Population standard deviation of period-over-period price returns.

    Uses the price series of the pool snapshots (>= 3 points required) to
    produce a simple 5-minute volatility proxy for the ML features.
    """
    prices = [s.pool.price for s in history if s.pool.price and s.pool.price > 0]
    if len(prices) < 3:
        return 0.0
    returns = [
        (prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))
    ]
    try:
        return float(statistics.pstdev(returns))
    except statistics.StatisticsError:
        return 0.0


class MonitorService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._provider = get_pool_provider()
        self._price_impact = get_price_impact_service()
        self._predictor = get_predictor()
        self._store = get_store()
        self._ws = get_ws_manager()
        self._watcher = get_mempool_watcher()
        self._market_maker = get_market_maker_bot()

    async def run(self) -> None:
        logger.info(
            "Monitor started (interval=%ss, mock=%s)",
            self._settings.scan_interval_seconds,
            self._settings.mock_mode,
        )
        self._watcher.start()
        while True:
            try:
                await self._scan_once()
            except asyncio.CancelledError:
                logger.info("Monitor cancelled")
                raise
            except Exception:  # noqa: BLE001 - keep the loop alive
                logger.exception("Monitor scan failed")
            await asyncio.sleep(self._settings.scan_interval_seconds)

    async def _scan_once(self) -> None:
        pending_swaps = len(self._watcher.drain_events())
        now = int(time.time())

        for entry in self._settings.watchlist:
            address = entry["address"]
            try:
                pool = self._provider.get_pool_state(entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping pool %s: %s", address, exc)
                continue

            pair = f"{pool.token0.symbol}/{pool.token1.symbol}"
            history = self._store.history(address, limit=self._settings.sample_history_size)

            change_1m = _pct_change(history, 60, pool.liquidity)
            change_5m = _pct_change(history, 300, pool.liquidity)
            change_15m = _pct_change(history, 900, pool.liquidity)
            volatility = _volatility(history)

            quote = self._price_impact.quote_usd(pool, _REFERENCE_TRADE_USD)
            impact_pct = quote.price_impact_pct if quote is not None else None

            features = build_feature_vector(
                liquidity_change_1m=change_1m,
                liquidity_change_5m=change_5m,
                liquidity_change_15m=change_15m,
                reference_impact_pct=abs(impact_pct) if impact_pct is not None else 0.0,
                pending_swaps=pending_swaps,
                fee_tier=pool.fee,
                liquidity=pool.liquidity,
                price_volatility_5m=volatility,
            )

            prediction = self._predictor.predict(
                features=features,
                liquidity_change_pct=change_1m,
                price_impact_pct=impact_pct,
                pair=pair,
                pool_address=address,
            )

            snapshot = PoolSnapshot(
                pool=pool,
                liquidity_change_pct_1m=change_1m,
                liquidity_change_pct_5m=change_5m,
                liquidity_change_pct_15m=change_15m,
                pending_swaps_1m=pending_swaps,
                reference_impact_pct=impact_pct,
            )
            self._store.add(snapshot)
            self._store.set_prediction(address, prediction)

            # Feed the signal into the execution layer (simulated AMM bot).
            action = await self._market_maker.evaluate_signal(prediction, pool.price)
            if action is not None:
                await self._ws.broadcast(
                    {"type": "bot", "data": self._market_maker.state()}
                )

            if prediction.alert_level in {"HIGH", "CRITICAL"}:
                alert = Alert(
                    level=prediction.alert_level,
                    pool_address=address,
                    pair=pair,
                    message=prediction.message,
                    drain_probability=prediction.drain_probability,
                    liquidity_change_pct=prediction.liquidity_change_pct,
                    price_impact_pct=prediction.price_impact_pct,
                    timestamp=now,
                )
                await self._ws.broadcast(alert.model_dump())
                logger.info("Alert [%s] %s", prediction.alert_level, prediction.message)

        # Push the latest pool snapshot so clients that connected while the
        # store was still empty (e.g. during a reload) recover on the next
        # scan, and so the pool table stays live.
        await self._ws.broadcast(
            {
                "type": "snapshot",
                "data": [s.pool.model_dump() for s in self._store.all_latest()],
            }
        )
