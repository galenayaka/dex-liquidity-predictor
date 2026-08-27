# Predictive Liquidity & Price Impact Analytics Dashboard — Backend

FastAPI backend that scans on-chain and mempool data to predict liquidity
drain and price impact on Uniswap v3 pools, and pushes warning indicators to
traders over WebSockets.

## Stack

- **FastAPI** — REST + WebSocket API
- **Web3.py** — Ethereum RPC reads and mempool subscriptions
- **Scikit-learn / XGBoost** — liquidity-drain classifier
- **Uvicorn** — ASGI server

## Project layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, exception handlers, /ws
│   ├── api/                    # REST routes + dependencies
│   ├── core/                   # settings, logging, exceptions, DI container
│   ├── ml/                     # features, XGBoost model, predictor
│   ├── schemas/                # Pydantic models
│   ├── services/               # web3 client, pool provider, price impact, mempool, store
│   ├── tasks/                  # background monitoring loop
│   └── websocket/              # connection manager
├── scripts/train_model.py      # trains the XGBoost model on synthetic data
├── tests/                      # unit tests
├── requirements.txt
└── .env.example
```

## Quickstart

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env        # Windows  (or: cp .env.example .env)

uvicorn app.main:app --reload --port 8000
```

The API is served at `http://localhost:8000` and interactive docs at
`http://localhost:8000/docs`.

### Run without a node

`MOCK_MODE=true` (the default in `.env.example`) makes the backend generate
synthetic pool, price and mempool data, so the whole dashboard runs offline.

### Connect to a real node

Set `MOCK_MODE=false` and fill in `RPC_URL_HTTP` / `RPC_URL_WS`. Never commit
provider API keys.

### Train the model

```bash
python -m scripts.train_model
```

This writes `models/liquidity_drain_model.json`. Without it the backend falls
back to a transparent rule-based heuristic.

## Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET  | `/api/v1/health` | Liveness / web3 connectivity |
| GET  | `/api/v1/pools` | Latest snapshot for every watched pool |
| GET  | `/api/v1/pools/{address}` | Latest snapshot for one pool |
| GET  | `/api/v1/pools/{address}/history` | Liquidity/price history |
| GET  | `/api/v1/metrics/{pool_address}` | Historical liquidity points (DB + in-memory fallback) |
| POST | `/api/v1/pools/{address}/price-impact` | Simulate a swap's price impact |
| GET  | `/api/v1/predictions/{address}` | Latest drain prediction |
| GET  | `/api/v1/predictions` | All latest predictions |
| WS   | `/ws` | Real-time alerts + snapshots + raw `Swap`/`Burn` events |

## Real-time event stream

The backend subscribes to the Uniswap v3 pool's `Swap` and `Burn` events over a
WebSocket RPC (`RPC_URL_WS`) and forwards every event to `/ws` clients:

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

Before an event reaches the client it is passed through `LiquidityPredictor`
(`app/services/liquidity_predictor.py`), which loads a `.pkl` model when present
(`LIQUIDITY_MODEL_PATH`) and otherwise falls back to a deterministic mock
inference. The result is attached to each event under `prediction`.

Large integers (wei amounts) are serialized as strings to avoid JavaScript
precision loss. Configure the watched pool via `UNISWAP_V3_POOL_ETH_USDC`.


## Security notes

- Addresses are validated and checksummed before use.
- No private keys are ever read or exposed; the backend is read-only.
- CORS is restricted to the configured frontend origins.
- Price-impact / prediction endpoints are rate limited per client IP.
- Errors never leak stack traces unless `DEBUG=true`.
