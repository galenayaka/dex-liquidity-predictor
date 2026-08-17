"""WebSocket connection manager with fan-out broadcast."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._connections:
            return
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for websocket in list(self._connections):
            try:
                await websocket.send_text(payload)
            except Exception:  # noqa: BLE001 - client went away
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
