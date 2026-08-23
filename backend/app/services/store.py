"""In-memory store for pool snapshots and predictions.

A lightweight thread-safe store keeps the backend dependency-free. Swap for a
database (MySQL) when persistence is required.
"""
from __future__ import annotations

import threading
from collections import defaultdict, deque

from ..schemas.pool import PoolSnapshot
from ..schemas.prediction import DrainPrediction


class SnapshotStore:
    def __init__(self, maxlen: int = 2000) -> None:
        self._maxlen = maxlen
        self._lock = threading.Lock()
        self._history: dict[str, deque[PoolSnapshot]] = defaultdict(lambda: deque(maxlen=maxlen))
        self._latest: dict[str, PoolSnapshot] = {}
        self._predictions: dict[str, DrainPrediction] = {}

    def add(self, snapshot: PoolSnapshot) -> None:
        address = snapshot.pool.address.lower()
        with self._lock:
            self._history[address].append(snapshot)
            self._latest[address] = snapshot

    def latest(self, address: str) -> PoolSnapshot | None:
        with self._lock:
            return self._latest.get(address.lower())

    def history(self, address: str, limit: int = 120) -> list[PoolSnapshot]:
        with self._lock:
            items = list(self._history[address.lower()])
            return items[-limit:]

    def all_latest(self) -> list[PoolSnapshot]:
        with self._lock:
            return list(self._latest.values())

    def set_prediction(self, address: str, prediction: DrainPrediction) -> None:
        with self._lock:
            self._predictions[address.lower()] = prediction

    def get_prediction(self, address: str) -> DrainPrediction | None:
        with self._lock:
            return self._predictions.get(address.lower())

    def all_predictions(self) -> list[DrainPrediction]:
        with self._lock:
            return list(self._predictions.values())
