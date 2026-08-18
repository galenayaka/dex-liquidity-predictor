"""FastAPI microservice exposing the crypto price forecast model.

Run:  uvicorn main:app --port 8100
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import FEATURE_COLUMNS, TARGET_TYPE, TICKERS
from data_source import fetch_all
from model import load_model, predict_with_uncertainty
from schemas import PredictRequest, PredictResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODELS: dict[str, tuple] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload any trained models so requests don't hit the disk each time.
    for key in TICKERS:
        try:
            MODELS[key] = load_model(key, TARGET_TYPE)
            logger.info("Loaded model for '%s'", key)
        except FileNotFoundError:
            logger.warning("No model for '%s' — run `python train.py` first", key)
    yield


app = FastAPI(
    title="Crypto Price Forecast",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the dashboard (served from any local origin) to call this service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "models_loaded": sorted(MODELS.keys())}


@app.get("/latest/{ticker}")
def latest(ticker: str) -> dict:
    """Return the most recent real feature snapshot to prefill the form."""
    key = ticker.lower()
    if key not in TICKERS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported ticker '{ticker}'. Use one of: {sorted(TICKERS)}.",
        )
    try:
        raw = fetch_all(key)  # cached for a day
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch latest data for %s: %s", key, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch latest data for '{key}': {exc}",
        ) from exc

    row = raw.iloc[-1]
    features: dict[str, float | None] = {}
    for name in FEATURE_COLUMNS:
        try:
            num = float(row[name])
        except (TypeError, ValueError):
            num = float("nan")
        features[name] = None if pd.isna(num) else round(num, 6)

    return {
        "ticker": key,
        "as_of": str(raw.index[-1].date()),
        "features": features,
    }


@app.post("/predict/{ticker}", response_model=PredictResponse)
def predict(ticker: str, body: PredictRequest) -> PredictResponse:
    key = ticker.lower()
    if key not in TICKERS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported ticker '{ticker}'. Use one of: {sorted(TICKERS)}.",
        )
    if key not in MODELS:
        raise HTTPException(
            status_code=503,
            detail=f"No model loaded for '{key}'. Run `python train.py --ticker {key}` first.",
        )

    model, meta = MODELS[key]
    features: list[str] = meta["features"]

    # Build a single-row frame in the exact persisted feature order.
    row = pd.DataFrame([{f: getattr(body, f) for f in features}])[features]

    return PredictResponse(**predict_with_uncertainty(model, row, meta))
