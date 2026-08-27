# 05 — API Reference

## 1. DEX backend (`backend/`, port 8000)

Base URL: `http://localhost:8000`. All routes are prefixed with `/api/v1`
except the WebSocket endpoint `/ws`. Interactive docs: `/docs`.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/health` | Liveness, version, chain id, mock mode, Web3 connectivity |
| GET | `/api/v1/pools` | Latest snapshot for every watched pool |
| GET | `/api/v1/pools/{address}` | Latest snapshot for one pool |
| GET | `/api/v1/pools/{address}/history?limit=` | Liquidity/price history |
| POST | `/api/v1/pools/{address}/price-impact` | Simulate a swap's price impact |
| GET | `/api/v1/predictions` | All latest drain predictions |
| GET | `/api/v1/predictions/{address}` | Latest prediction for one pool |
| GET | `/api/v1/metrics/{pool_address}?time_range=` | Historical liquidity points (1h/24h/7d) |
| GET | `/api/v1/market-maker/status` | Bot's current (simulated) position state |
| POST | `/api/v1/users/register` | Register a user (bcrypt-hashed password) |
| WS | `/ws` | Real-time alerts, snapshots, events, bot state |

`GET /api/v1/metrics/{pool_address}` returns persisted `liquidity_metrics`
rows; when a pool has none (mock mode, fresh install, or MySQL offline) it
falls back to the in-memory snapshot history so the chart still renders.

### 1.1 Price-impact simulation

```http
POST /api/v1/pools/{address}/price-impact
Content-Type: application/json

{ "token_in": "0x...token0...", "amount_in": 1000.0 }
```

Response (`PriceImpactResponse`):

```json
{
  "pool_address": "0x...",
  "token_in": "0x...",
  "token_out": "0x...",
  "amount_in": 1000.0,
  "amount_out": 0.3,
  "price_before": 0.0003,
  "price_after": 0.000297,
  "price_impact_pct": -1.0
}
```

`price_impact_pct` is negative when the price moves against the trader.

### 1.2 Market-maker status

```http
GET /api/v1/market-maker/status
```

```json
{
  "has_active_position": false,
  "tick_lower": 0,
  "tick_upper": 0,
  "liquidity": 0,
  "token_id": null,
  "simulation_mode": true,
  "tick_spacing": 60,
  "accumulated_fees": 0.0,
  "current_impermanent_loss": 0.0,
  "net_portfolio_value": 0.0,
  "sharpe_ratio": 0.0
}
```

## 2. Forecast service (`crypto-forecast/`, port 8100)

Base URL: `http://localhost:8100`.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Status + models loaded + supported tickers |
| GET | `/snapshot` | Live price + 24h change per ticker, plus macro series |
| GET | `/latest/{ticker}` | Most recent real feature snapshot (prefills the form) |
| GET | `/predict/{ticker}` | Predict next-day price from the latest live data |
| POST | `/predict/{ticker}` | Predict from a manually supplied feature snapshot |

Supported tickers: `btc`, `eth`, `sol`, `bnb`, `xrp`.

### 2.1 Manual prediction

```http
POST /predict/btc
Content-Type: application/json

{
  "open": 65000, "high": 66200, "low": 64800, "close": 65900, "volume": 3.2e10,
  "sp500_close": 5300, "dxy": 104.2, "gold": 2350, "treasury_10y": 4.25, "gpr": 95
}
```

Response (regression):

```json
{
  "ticker": "btc",
  "target_type": "regression",
  "predicted_price": 66410.2,
  "confidence": 92.1,
  "interval_low": 65100.0,
  "interval_high": 67720.0,
  "model_rmse": 1500.0,
  "model_mae": 1150.0,
  "model_r2": 0.87,
  "ensemble_size": 1
}
```

## 3. WebSocket protocol (backend `/ws`)

Endpoint: `ws://localhost:8000/ws`. The server is **push-only**; inbound client
messages are ignored. Frames are JSON with a `type` discriminator.

| Direction | `type` | Payload |
| --- | --- | --- |
| Server → client (connect) | `snapshot` | `{"type":"snapshot","data":[PoolState, …]}` |
| Server → client (event) | `event` | Swap/Burn event + `prediction` + `raw` log |
| Server → client (alert) | `alert` | HIGH/CRITICAL warning (`level`, `pair`, `message`, …) |
| Server → client (bot) | `bot` | `{"type":"bot","data": MarketMakerState}` |

### 3.1 Event frame

```json
{
  "type": "event",
  "event": "Swap",
  "pool": "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8",
  "pair": "ETH/USDC",
  "transaction_hash": "0x...",
  "block_number": 19800000,
  "args": { "amount0": "-1000000000000000000", "amount1": "3000000000", "tick": -198000 },
  "prediction": {
    "predicted_drain_percentage": 0.61,
    "predicted_price_impact": 0.17,
    "risk_level": "Low"
  },
  "raw": { "topics": ["0xc42079f9..."], "data": "0x...", "log_index": 12 },
  "timestamp": 1723891200
}
```

Large integers (wei amounts) are serialized as strings to avoid JavaScript
precision loss.

### 3.2 Alert frame

```json
{
  "type": "alert",
  "level": "HIGH",
  "pool_address": "0x...",
  "pair": "USDC/WETH",
  "message": "Warning: USDC/WETH pool is predicted to experience a 18.0% liquidity drain",
  "drain_probability": 0.72,
  "liquidity_change_pct": -0.18,
  "price_impact_pct": -0.04,
  "timestamp": 1723891200
}
```

## 4. Error format

Backend errors use a consistent JSON envelope (see `core/exceptions.py`):

```json
{
  "error": {
    "code": "not_found",
    "message": "No prediction for pool 0x... yet",
    "details": null
  }
}
```

Common codes: `not_found`, `price_impact_error`, `database_unavailable`,
`email_taken`, `internal_error`. Stack traces are only included when
`DEBUG=true`.

## 5. Rate limiting

Price-impact and per-pool prediction endpoints are rate-limited per client IP
(`api/deps.py`, `rate_limit_dependency`).
