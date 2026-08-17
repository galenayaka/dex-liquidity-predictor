"""Liquidity-drain prediction endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.exceptions import NotFoundError
from ...schemas.prediction import PredictionResponse
from ..deps import get_store, rate_limit_dependency

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
def list_predictions():
    predictions = get_store().all_predictions()
    return {"count": len(predictions), "predictions": predictions}


@router.get(
    "/{address}",
    response_model=PredictionResponse,
    dependencies=[Depends(rate_limit_dependency)],
)
def get_prediction(address: str):
    prediction = get_store().get_prediction(address)
    if prediction is None:
        raise NotFoundError(f"No prediction for pool {address} yet")
    return PredictionResponse(prediction=prediction)
