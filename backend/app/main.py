"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import api_router
from .core.config import get_settings
from .core.container import get_event_listener, get_store, get_ws_manager
from .core.exceptions import AppError
from .core.logging import setup_logging
from .db.database import init_db
from .tasks.monitor import MonitorService

logger = logging.getLogger(__name__)

settings = get_settings()
setup_logging(settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database tables initialized")
    except Exception:  # noqa: BLE001 - PostgreSQL may be offline in dev/mock mode
        logger.warning("Skipped database initialization (PostgreSQL unreachable)")

    monitor = MonitorService()
    event_listener = get_event_listener()
    monitor_task = asyncio.create_task(monitor.run())
    events_task = asyncio.create_task(event_listener.run())
    logger.info("Application started (mock_mode=%s)", settings.mock_mode)
    try:
        yield
    finally:
        event_listener.stop()
        monitor_task.cancel()
        events_task.cancel()
        await asyncio.gather(monitor_task, events_task, return_exceptions=True)
        logger.info("Application stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    message = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": message}},
    )


app.include_router(api_router, prefix="/api/v1")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager = get_ws_manager()
    await manager.connect(websocket)
    try:
        snapshots = get_store().all_latest()
        await websocket.send_text(
            json.dumps(
                {"type": "snapshot", "data": [s.pool.model_dump() for s in snapshots]},
                default=str,
            )
        )
        while True:
            # Incoming messages are ignored; the server only pushes.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:  # noqa: BLE001
        manager.disconnect(websocket)
