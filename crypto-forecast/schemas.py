"""Pydantic request/response schemas for the prediction API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """Latest feature snapshot used to forecast the next day's price."""

    open: float = Field(..., description="Today's open price")
    high: float = Field(..., description="Today's high price")
    low: float = Field(..., description="Today's low price")
    close: float = Field(..., description="Today's close price")
    volume: float = Field(..., description="Today's trading volume")
    sp500_close: float = Field(..., description="S&P 500 closing price")
    dxy: float = Field(..., description="US Dollar Index (DXY)")
    gold: float = Field(..., description="Gold price (USD/oz)")
    treasury_10y: float = Field(..., description="10-Year Treasury yield (%)")
    gpr: float = Field(..., description="Geopolitical Risk (GPR) index")


class PredictResponse(BaseModel):
    ticker: str
    target_type: str
    predicted_price: float | None = None
    predicted_direction: int | None = None
    probability_up: float | None = None
    confidence: float | None = None
    interval_low: float | None = None
    interval_high: float | None = None
    model_rmse: float | None = None
    model_mae: float | None = None
    model_r2: float | None = None
    model_accuracy: float | None = None
    ensemble_size: int | None = None
