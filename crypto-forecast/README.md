# Crypto Price Forecast — ML Pipeline & FastAPI Microservice

A supervised machine-learning pipeline that predicts the next-day price of
**BTC** and **ETH** from crypto OHLCV, macroeconomic indicators, and geopolitical
risk, served through a FastAPI endpoint.

```
crypto-forecast/
├── config.py          # tickers, feature columns, FRED series, split, seed
├── data_source.py     # yfinance / FRED / GPR fetching + caching
├── features.py        # target construction + aligned feature matrix
├── model.py           # XGBoost(+HistGBM) ensemble, evaluation, persistence
├── schemas.py         # Pydantic request/response models
├── main.py            # FastAPI app (/health, /predict/{ticker})
├── train.py           # end-to-end training CLI
├── requirements.txt
└── .env.example
```

## Features

| Group        | Series                                                            |
| ------------ | ----------------------------------------------------------------- |
| Crypto       | BTC-USD / ETH-USD: open, high, low, close, volume (`yfinance`)     |
| Equities     | S&P 500 close (`^GSPC`)                                            |
| Macro        | US Dollar Index (DXY), Gold, 10-Year Treasury yield                |
| Geopolitical | Geopolitical Risk (GPR) index (Iacoviello hosted CSV)              |
| Target       | next-day close (regression) or up/down direction (classification)  |

- **Weekend gaps**: traditional-market series are forward-filled onto the
  crypto's 7-day calendar.
- **Leakage control**: chronological 80/20 split (no shuffling) — the model is
  only ever evaluated on strictly future data.
- **Scaling**: `StandardScaler` is applied inside the pipeline.

## Setup

```bash
cd crypto-forecast
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` and set `FRED_API_KEY` to pull macro
series from the Federal Reserve. **Without a key the pipeline automatically
falls back to `yfinance` proxies**, so it runs out of the box.

## Train

```bash
python train.py --ticker btc                    # regression (next-day close)
python train.py --ticker eth --target classification
python train.py --ticker btc --no-ensemble      # plain XGBoost
```

This fetches data (cached for a day in `data/`), builds features, trains,
prints the evaluation metrics, and saves the model + metadata to `models/`.

Reported metrics (regression): **MAE**, **RMSE**, **R²**; (classification):
**accuracy** and a full classification report.

## Serve & predict

```bash
uvicorn main:app --port 8100
```

```bash
curl -X POST http://localhost:8100/predict/btc \
  -H "Content-Type: application/json" \
  -d '{
        "open": 65000, "high": 66200, "low": 64800, "close": 65900, "volume": 3.2e10,
        "sp500_close": 5300, "dxy": 104.2, "gold": 2350, "treasury_10y": 4.25, "gpr": 95
      }'
```

Response (regression):

```json
{ "ticker": "btc", "target_type": "regression", "predicted_price": 66410.2, ... }
```

## Notes

- The endpoint accepts exactly the feature snapshot (today's OHLCV + macro +
  GPR) and returns the next-day forecast. Feature order is read from the saved
  metadata, so it always matches the trained model.
- To add engineered features (lags, rolling volatility), extend
  `FEATURE_COLUMNS`, rebuild, and add the same fields to `PredictRequest`.
