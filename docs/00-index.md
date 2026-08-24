# DEX Liquidity Predictor — Documentation

> **Thesis / conference topic:** *Predicting Liquidity Dynamics and Price Impact
> in Decentralized Exchanges: A Machine Learning Approach to Algorithmic Market
> Making on Distributed Ledgers.*

This folder contains the full documentation set for the **DEX Liquidity
Predictor** repository. It is written to support two use cases:

1. **A thesis** on the title above.
2. **An international conference paper** on the same topic.

Every claim here is backed by the actual code in `backend/`, `crypto-forecast/`
and `frontend/`. Where a document references a module, the file path is given so
you can cite it directly. The root `README.md` remains the "how to run it" guide;
this folder is the "what it is, why it works, and how to write about it" guide.

## Index

| Document | Contents |
| --- | --- |
| [`01-abstract.md`](01-abstract.md) | Thesis / conference abstract + keywords |
| [`02-architecture.md`](02-architecture.md) | System architecture & data flow |
| [`03-methodology.md`](03-methodology.md) | ML methodology & mathematics |
| [`04-market-making.md`](04-market-making.md) | Algorithmic market-making strategy |
| [`05-api-reference.md`](05-api-reference.md) | REST + WebSocket API reference |
| [`06-conference-paper.md`](06-conference-paper.md) | Conference paper abstract & outline |
| [`07-thesis-guide.md`](07-thesis-guide.md) | Mapping the code to thesis chapters |

## Quick facts

| Attribute | Value |
| --- | --- |
| Services | 3 (backend :8000, forecast :8100, dashboard :3000) |
| Backend runtime | Python 3.11+ · FastAPI + Uvicorn |
| Forecast runtime | Python 3.11+ · FastAPI + XGBoost |
| Dashboard runtime | Next.js 14 + React 18 + Tailwind CSS |
| ML libraries | scikit-learn, XGBoost |
| Blockchain | Ethereum + Uniswap v3 (Web3.py); mock mode runs fully offline |
| Database | MySQL (optional, best-effort persistence) |

## How the title maps to the system

| Title phrase | Subsystem | Where |
| --- | --- | --- |
| *Predicting Liquidity Dynamics* | Liquidity-drain classifier (XGBoost + heuristic) | `backend/app/ml/` |
| *and Price Impact* | Exact Uniswap v3 swap math + impact quotes | `backend/app/services/price_impact.py` |
| *in Decentralized Exchanges* | Uniswap v3 Swap/Burn event stream + mempool | `backend/app/services/`, `backend/app/tasks/` |
| *A Machine Learning Approach* | XGBoost classifiers & quantile regressors | `backend/app/ml/`, `crypto-forecast/` |
| *to Algorithmic Market Making* | Reactive liquidity-provision bot | `backend/app/services/market_maker.py` |
| *on Distributed Ledgers* | Web3.py read/write layer, on-chain AMM | `backend/app/services/web3_client.py`, `market_maker.py` |
