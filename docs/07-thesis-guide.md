# 07 — Thesis Guide

How to map this repository to the chapters of a thesis titled *"Predicting
Liquidity Dynamics and Price Impact in Decentralized Exchanges: A Machine
Learning Approach to Algorithmic Market Making on Distributed Ledgers."*

## Chapter-by-chapter mapping

### Chapter 1 — Introduction
- Problem statement: AMM liquidity is volatile; providers need early warning of
  drains and a measure of price impact before trading.
- Motivation: growing DeFi TVL, impermanent loss, slippage costs.
- Research questions (mirror `03-methodology.md` §1).
- Contributions & thesis structure.

### Chapter 2 — Background & Literature Review
- **AMMs & Uniswap v3**: constant-product invariant, concentrated liquidity,
  tick ranges, `1.0001^tick` pricing, Q64.96 fixed point.
- **Price impact / slippage**: exact-input swap math.
- **Liquidity provision risk**: impermanent loss, fee accrual.
- **ML for finance**: gradient boosting, quantile regression.
- Prior work on DeFi risk monitoring and crypto forecasting.

### Chapter 3 — System Design
- Use `02-architecture.md`: three services, data flow, module maps, and the
  graceful-degradation strategy (mock mode, heuristic fallback, simulation
  toggle).

### Chapter 4 — Methodology
- §4.1 Liquidity-drain prediction (features, XGBoost, heuristic) —
  `03-methodology.md` §3.
- §4.2 Price-impact mathematics — `03-methodology.md` §4.
- §4.3 Quantile forecasting — `03-methodology.md` §5.
- §4.4 Algorithmic market-making policy — `04-market-making.md`.

### Chapter 5 — Implementation
- Backend FastAPI structure, Web3.py integration, WebSocket protocol.
- Forecast pipeline (`data_source.py`, `features.py`, `model.py`, `main.py`).
- Frontend dashboard (views, hooks, command line).

### Chapter 6 — Experiments & Evaluation
- Metrics: MAE/RMSE/R² (forecast); drain probability thresholds.
- Model vs. heuristic fallback comparison.
- Leakage-control demonstration (chronological vs. shuffled split).
- Simulated market-maker portfolio metrics (fees, IL, Sharpe).

### Chapter 7 — Discussion & Conclusion
- Strengths, limitations, future work (real-data training, gas oracles,
  slippage limits, backtesting).

## Thesis talking points the code directly supports

1. **Real-time DeFi risk monitoring** — raw blockchain events decoded, enriched
   with ML, streamed over WebSockets (`tasks/monitor.py`, `main.py`).
2. **Uniswap v3 price-impact modeling** — exact integer arithmetic replicating
   the core contracts (`services/price_impact.py` + `tests/test_price_impact.py`).
3. **Liquidity-drain prediction** — feature engineering from pool snapshots and
   an XGBoost classifier with a transparent baseline
   (`ml/features.py`, `ml/predictor.py`).
4. **Uncertainty-aware forecasting** — quantile gradient boosting for a 95%
   interval with a chronological split (`crypto-forecast/model.py`).
5. **Multi-source data alignment** — merging 7-day crypto data with 5-day macro
   series via forward fill (`crypto-forecast/data_source.py`).
6. **Graceful degradation** — every ML component has a deterministic fallback;
   every external dependency degrades instead of crashing.

## Reproducibility

- Run everything offline with `MOCK_MODE=true` + `SIMULATION_MODE=true`
  (defaults).
- Train the drain classifier: `python -m scripts.train_model`.
- Train the forecast models: `python train.py --all`.
- Unit tests: `python -m pytest` (in `backend/`).

## Suggested extensions for stronger research contributions

- Replace synthetic drain-training data with labeled historical on-chain data.
- Add engineered forecast features (lags, rolling volatility, sentiment).
- Backtest the market-maker policy against historical Uniswap v3 data.
- Implement a proper gas oracle and slippage limits for the real execution path.
- Add formal uncertainty calibration (e.g., PIT histograms for quantiles).
