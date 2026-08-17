"""Health check."""
from __future__ import annotations

from fastapi import APIRouter

from ...core.config import get_settings
from ...core.container import get_web3_client
from ...schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    client = get_web3_client()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
        chain_id=settings.chain_id,
        mock_mode=settings.mock_mode,
        web3_connected=client.is_connected(),
    )
