"""FastAPI dependencies: DI accessors + a lightweight rate limiter."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from ..core.exceptions import AppError
from ..core.container import (
    get_pool_provider,
    get_price_impact_service,
    get_predictor,
    get_store,
    get_web3_client,
)


class SlidingWindowRateLimiter:
    """Fixed-window-per-key limiter; adequate for a single-process API."""

    def __init__(self, limit: int = 120, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            dq = self._hits[key]
            while dq and now - dq[0] > self.window:
                dq.popleft()
            if len(dq) >= self.limit:
                return False
            dq.append(now)
            return True


_limiter = SlidingWindowRateLimiter(limit=120, window_seconds=60)


async def rate_limit_dependency(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    if not _limiter.allow(key):
        raise AppError(
            "Rate limit exceeded. Please retry shortly.",
            status_code=429,
            code="rate_limited",
        )


# Re-export accessors so route handlers keep a single import source.
__all__ = [
    "get_pool_provider",
    "get_price_impact_service",
    "get_predictor",
    "get_store",
    "get_web3_client",
    "rate_limit_dependency",
]
