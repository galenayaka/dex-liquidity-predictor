"""Aggregate API router."""
from __future__ import annotations

from fastapi import APIRouter

from .routes import health, pools, predictions, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(pools.router)
api_router.include_router(predictions.router)
api_router.include_router(users.router)
