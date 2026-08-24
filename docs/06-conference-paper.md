# 06 — Conference Paper: Abstract & Outline

A ready-to-adapt skeleton for an international conference submission.

## Title

**Predicting Liquidity Dynamics and Price Impact in Decentralized Exchanges:
A Machine Learning Approach to Algorithmic Market Making on Distributed
Ledgers**

## Abstract (draft)

Decentralized exchanges (DEXs) built on automated market makers have become core
distributed-ledger financial infrastructure, yet their liquidity is volatile and
difficult to anticipate. Liquidity providers face two coupled risks: the sudden
withdrawal of capital from a pool (a *liquidity drain*) and the market impact a
trade imposes on a shallow pool (*price impact*). This paper presents an
end-to-end system that predicts both quantities in real time and translates the
predictions into an algorithmic market-making policy. A monitoring backend
ingests Uniswap v3 `Swap`/`Burn` events and mempool transactions, extracts a
fixed feature vector, and feeds a gradient-boosted classifier (XGBoost) that
estimates imminent-drain probability, with a transparent rule-based fallback for
graceful degradation. A price-impact engine reproduces the exact Q64.96
fixed-point arithmetic of the Uniswap v3 core contracts to simulate exact-input
swaps. A forecasting microservice trains a quantile XGBoost regressor per asset
on crypto, equity, macroeconomic and geopolitical-risk features, producing a
next-day point forecast with a 95% predictive interval under a chronological
train/test split. The signals drive a reactive market-making agent that withdraws
liquidity at high risk and provides concentrated liquidity at low risk, widening
its tick range in proportion to predicted impact. Real on-chain execution is
provided as Web3.py transaction boilerplate behind a simulation toggle, and a
WebSocket-driven dashboard renders the signals in real time. The system offers a
reproducible reference architecture connecting blockchain data, financial
mathematics and machine learning into executable market-making decisions.

**Keywords:** decentralized exchange; automated market maker; Uniswap v3;
liquidity prediction; price impact; algorithmic market making; XGBoost; quantile
regression; blockchain.

## Paper outline (IMRaD)

### 1. Introduction
- Growth of DEXs and AMMs; why liquidity provision is risky.
- The three questions (drain, impact, outlook) and how ML addresses them.
- Contributions (list from the abstract).

### 2. Background & Related Work
- AMMs and Uniswap v3 concentrated liquidity, Q64.96 prices, tick ranges.
- Impermanent loss; price impact / slippage.
- Prior work on liquidity prediction and on ML for crypto forecasting.
- Gap: end-to-end prediction → execution loop.

### 3. System Design
- Three-service architecture (see `02-architecture.md`).
- Data sources and the mock/simulation degradation strategy.

### 4. Methodology
- Liquidity-drain classifier: features, XGBoost, heuristic fallback
  (`03-methodology.md` §3).
- Price-impact mathematics (`03-methodology.md` §4).
- Quantile forecasting & leakage control (`03-methodology.md` §5).
- Market-making policy (`04-market-making.md`).

### 5. Experiments & Results
- Evaluation metrics (MAE/RMSE/R² for regression; drain probability thresholds).
- Ablation: XGBoost vs. heuristic; chronological vs. shuffled split.
- Simulated market-maker portfolio metrics (fees, IL, Sharpe ratio).

### 6. Discussion
- Strengths: exact on-chain math, graceful degradation, transparency.
- Limitations: synthetic training data, linear slippage approximations in mock
  inference, naive gas strategy in the real path.

### 7. Conclusion & Future Work
- Recapitulate contributions; propose real-data training, gas oracles,
  slippage limits, and backtesting.

## Suggested figures & tables

1. **Figure 1** — system architecture (reuse the mermaid diagram in
   `02-architecture.md`).
2. **Table 1** — the 8 drain-classifier features (`03-methodology.md` §3.1).
3. **Figure 2** — data-flow sequence diagram (blockchain → backend → dashboard).
4. **Table 2** — heuristic fallback weights (`03-methodology.md` §3.4).
5. **Figure 3** — forecast with 95% interval (quantile bounds).
6. **Table 3** — market-maker policy state machine (`04-market-making.md` §2).
