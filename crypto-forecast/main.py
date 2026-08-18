"""FastAPI microservice exposing the crypto price forecast model.

Run:  uvicorn main:app --port 8100
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import FEATURE_COLUMNS, TICKERS
from data_source import fetch_all
from model import load_model, predict_with_uncertainty
from schemas import PredictRequest, PredictResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODELS: dict[str, tuple] = {}


def _clean_number(value) -> float | None:
    """Coerce a cell to a JSON-safe float (None when missing/NaN)."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(num) else num


def _latest_row(ticker: str) -> tuple[pd.Series, str]:
    """Most recent complete row + its date for a ticker (cached for a day)."""
    raw = fetch_all(ticker)
    return raw.iloc[-1], str(raw.index[-1].date())


def _require_ticker(ticker: str) -> str:
    key = ticker.lower()
    if key not in TICKERS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported ticker '{ticker}'. Use one of: {sorted(TICKERS)}.",
        )
    return key


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload any trained models so requests don't hit the disk each time.
    for key in TICKERS:
        try:
            MODELS[key] = load_model(key)
            logger.info("Loaded model for '%s'", key)
        except FileNotFoundError:
            logger.warning("No model for '%s' — run `python train.py --ticker %s`", key, key)
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
    return {
        "status": "ok",
        "models_loaded": sorted(MODELS.keys()),
        "tickers": sorted(TICKERS.keys()),
    }


@app.get("/latest/{ticker}")
def latest(ticker: str) -> dict:
    """Return the most recent real feature snapshot to prefill the form."""
    key = _require_ticker(ticker)
    try:
        row, as_of = _latest_row(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch latest data for %s: %s", key, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch latest data for '{key}': {exc}",
        ) from exc

    features = {name: _clean_number(row[name]) for name in FEATURE_COLUMNS}
    return {"ticker": key, "as_of": as_of, "features": features}


@app.get("/snapshot")
def snapshot() -> dict:
    """Market monitor: live price + 24h change per ticker, plus macro series."""
    result: dict = {"as_of": None}
    macro_fields = ("sp500_close", "dxy", "gold", "treasury_10y", "gpr")

    for key in sorted(TICKERS):
        try:
            raw = fetch_all(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Snapshot: could not fetch %s: %s", key, exc)
            continue
        closes = raw["close"]
        price = _clean_number(closes.iloc[-1])
        prev = _clean_number(closes.iloc[-2]) if len(closes) >= 2 else None
        change = None
        if price is not None and prev is not None and prev > 0:
            change = round((price - prev) / prev * 100.0, 2)
        result[key] = {"price": price, "change_24h": change}

        if result["as_of"] is None:
            result["as_of"] = str(raw.index[-1].date())
            for name in macro_fields:
                result[name] = _clean_number(raw.iloc[-1][name])

    return result


@app.get("/predict/{ticker}")
def predict_live(ticker: str) -> dict:
    """Predict the next-day price from the latest live data (dynamic routing)."""
    key = _require_ticker(ticker)
    if key not in MODELS:
        raise HTTPException(
            status_code=404,
            detail=f"No model trained for '{key}'. Run `python train.py --ticker {key}` first.",
        )
    try:
        row, as_of = _latest_row(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch live data for %s: %s", key, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch live data for '{key}': {exc}",
        ) from exc

    booster, meta = MODELS[key]
    frame = pd.DataFrame([{f: _clean_number(row[f]) for f in meta["features"]}])[meta["features"]]
    out = predict_with_uncertainty(booster, frame, meta)
    out["as_of"] = as_of
    return out


@app.post("/predict/{ticker}", response_model=PredictResponse)
def predict_manual(ticker: str, body: PredictRequest) -> PredictResponse:
    """Predict from a manually supplied feature snapshot (advanced form)."""
    key = _require_ticker(ticker)
    if key not in MODELS:
        raise HTTPException(
            status_code=404,
            detail=f"No model trained for '{key}'. Run `python train.py --ticker {key}` first.",
        )

    booster, meta = MODELS[key]
    row = pd.DataFrame([{f: getattr(body, f) for f in meta["features"]}])[meta["features"]]
    return PredictResponse(**predict_with_uncertainty(booster, row, meta))
