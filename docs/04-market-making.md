# 04 — Algorithmic Market-Making Strategy

`backend/app/services/market_maker.py` implements the **execution counterpart**
to the prediction pipeline. The predictors answer *"what is likely to happen to
this pool?"*; the `MarketMakerBot` answers *"and what should we do about it?"*.

## 1. Overview

The bot manages a **simulated Uniswap v3 concentrated-liquidity position**:

- It remembers whether a position is open and its tick range (stateful).
- On every new prediction it applies a **reactive policy**.
- The tick range is **dynamic**: higher predicted price impact widens the range
  (more volatility); lower impact narrows it (more concentrated).
- Real on-chain execution is implemented as Web3.py boilerplate behind the
  `SIMULATION_MODE` toggle (default **on**), so nothing is signed or broadcast
  unless explicitly enabled.

## 2. Reactive policy (state machine)

`evaluate_signal(prediction, current_price)` normalizes either a
`DrainPrediction` (monitor loop) or the dict from `LiquidityPredictor.predict`
(event stream), then applies:

| Condition | Action |
| --- | --- |
| Risk ∈ {HIGH, CRITICAL} **and** position open | `withdraw_liquidity` (protect capital from impermanent loss) |
| Risk == LOW **and** no position | `provide_liquidity` (deploy capital) |
| Otherwise (MEDIUM, or already in the right state) | hold (`None`) |

The frontend summarizes this as:
`withdraw on HIGH/CRITICAL · provide on LOW · hold otherwise`.

## 3. Tick-range sizing

Uniswap v3 encodes price as `price = 1.0001 ** tick`, so:

```
tick = ln(price) / ln(1.0001)
```

`calculate_optimal_ticks`:

1. Anchors the center on the tick nearest the current price, adjusting for token
   decimals (`P_raw = P_human · 10^(decimals1 − decimals0)`).
2. Snaps the center to a multiple of the pool's `tick_spacing` (60 = 0.3% fee
   tier).
3. Widens symmetrically by `steps = 1 + int(impact / 5)` per side, clamped to
   `max_range_steps` (default 10).

```
tick_lower = center − steps · spacing
tick_upper = center + steps · spacing
```

Thus a 0% predicted impact yields a maximally concentrated 2-spacing range, and
each +5% of impact widens it by one step.

## 4. Simulation vs. real execution

### Simulated (default)

- `provide_liquidity` sets `has_active_position=True` and records the computed
  tick range with a placeholder `position_liquidity = 1,000,000`.
- `withdraw_liquidity` clears the position state.
- Actions are logged as `[SIMULATION] Mint/Burn liquidity in range [...]`.

### Real (opt-in)

When `SIMULATION_MODE=false` and `WALLET_PRIVATE_KEY`/`WALLET_ADDRESS` are set:

- **Mint** calls `NonfungiblePositionManager.mint(...)` with `amount0/amount1`,
  `tickLower/tickUpper`, `amount0Min/amount1Min=0`, `recipient`, and a 5-minute
  deadline (`services/market_maker.py`, `_send_mint`).
- **Burn** calls `decreaseLiquidity(tokenId, liquidity=0, …)` then
  `collect(tokenId, recipient, …)` (`_send_decrease_and_collect`).
- Transactions are built with a naive EIP-1559 fee strategy and signed with the
  configured key (`_sign_and_send`).

> The code notes this is boilerplate: a production system should use a proper
> gas oracle and slippage limits.

## 5. Financial tracking (simulated)

While a position is open, the bot tracks portfolio economics for evaluation:

| Field | Meaning | Schema |
| --- | --- | --- |
| `accumulated_fees` | Simulated trading-fee accrual (USD) | `MarketMakerStatus` |
| `current_impermanent_loss` | IL relative to holding outside the pool | `MarketMakerStatus` |
| `net_portfolio_value` | Total value of the position | `MarketMakerStatus` |
| `sharpe_ratio` | Risk-adjusted return of the strategy | `MarketMakerStatus` |
| `portfolio_history` | Per-evaluation snapshots | internal |

The fee accrual is kept small (`0.01` USD/eval) so portfolio growth is dominated
by price moves rather than fee drift.

## 6. ABI fragments

The bot declares only the minimal `NonfungiblePositionManager` ABI fragments it
uses — `mint`, `decreaseLiquidity`, and `collect` — rather than the full
contract ABI, keeping the dependency surface small and reviewable.
