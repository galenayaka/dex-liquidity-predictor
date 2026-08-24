# Abstract

## Title

**Predicting Liquidity Dynamics and Price Impact in Decentralized Exchanges:
A Machine Learning Approach to Algorithmic Market Making on Distributed
Ledgers**

## Abstract

Decentralized exchanges (DEXs) powered by automated market makers (AMMs) have
become a core component of the distributed-ledger financial infrastructure, yet
the liquidity they rely on is both volatile and difficult to anticipate.
Liquidity providers face two intertwined risks: the sudden withdrawal of
liquidity from a pool (a *liquidity drain*) and the market impact that a trade
imposes on a shallow pool (*price impact* / slippage). This work presents an
end-to-end system that predicts both quantities in real time and uses those
predictions to drive an algorithmic market-making policy.

The system is composed of three cooperating services. First, a **monitoring
backend** ingests Uniswap v3 `Swap` and `Burn` events and pending mempool
transactions, extracts a fixed feature vector (short-horizon liquidity changes,
reference-trade price impact, mempool pressure, fee tier, log-liquidity and
5-minute price volatility), and feeds it to a gradient-boosted decision-tree
classifier (XGBoost) that estimates the probability of an imminent liquidity
drain. When no trained model is available, a transparent rule-based heuristic
provides a deterministic fallback, guaranteeing graceful degradation. Second, a
**price-impact engine** reproduces the exact integer arithmetic of the Uniswap
v3 core contracts (Q64.96 fixed-point square-root prices) to simulate exact-input
swaps and quantify price impact without approximation. Third, a **forecasting
microservice** trains a quantile XGBoost regressor per asset on crypto OHLCV,
equity, macroeconomic and geopolitical-risk features to produce a next-day price
point forecast together with a 95% predictive interval, using a chronological
train/test split to avoid look-ahead bias.

The predictions are consumed by a **reactive market-making agent** that manages a
simulated Uniswap v3 concentrated-liquidity position: it withdraws liquidity when
risk is high to protect capital from impermanent loss, provides concentrated
liquidity when risk is low, and dynamically widens or narrows its tick range in
proportion to predicted price impact. Real on-chain execution is implemented as
Web3.py transaction boilerplate behind a simulation toggle. A real-time dashboard
renders the resulting risk signals as live tables, charts and alerts over a
WebSocket channel.

The contribution is a reference architecture that ties blockchain event data,
financial mathematics and machine learning into a single reproducible pipeline,
demonstrating how predictive models can be translated into executable
market-making decisions on a distributed ledger.

## Keywords

- Decentralized exchange (DEX)
- Automated market maker (AMM)
- Uniswap v3
- Liquidity prediction
- Price impact / slippage
- Algorithmic market making
- XGBoost
- Quantile regression
- Blockchain / distributed ledger
- WebSocket real-time analytics

## Scope & disclaimer

This is an educational / research demonstration system. It is **not** financial
advice. The predictions are statistical estimates of historical patterns and do
not anticipate black-swan events. Default `MOCK_MODE` and `SIMULATION_MODE`
settings generate synthetic data and simulate executions so the entire pipeline
runs offline and reproducibly; the same code paths connect to live Ethereum RPC
endpoints when configured.
