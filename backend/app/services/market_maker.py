"""Algorithmic Market Making — simulated execution layer.

`MarketMakerBot` is the *execution* counterpart to the ML prediction pipeline.
The predictors elsewhere in the backend answer "what is likely to happen to this
pool?"; this bot answers "and what should we do about it?".

It manages a **simulated** Uniswap v3 liquidity position:

- It keeps the current position state (whether one is open and its tick range).
- On every new prediction it applies a simple reactive policy:
    * HIGH / CRITICAL risk + open position  -> withdraw (protect capital from
      impermanent loss).
    * LOW risk + no position                -> provide (concentrated) liquidity.
- The tick range is dynamic: a higher predicted price impact widens the range
  (more volatility), a lower one narrows it (more concentrated).

Real on-chain execution is implemented as `web3.py` boilerplate behind the
`SIMULATION_MODE` toggle (default on), so nothing is ever signed or broadcast
unless explicitly enabled.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

import numpy as np

from ..core.config import Settings

logger = logging.getLogger(__name__)

# Uniswap v3 encodes price as `price = 1.0001 ** tick`, therefore:
#   tick = ln(price) / ln(1.0001)
_TICK_BASE = 1.0001

# Fallback human price of token0 (USDC) denominated in token1 (WETH), used when
# no market price has been observed yet (~1 USDC = 0.0003 WETH).
_FALLBACK_PRICE = 0.0003

# Simulated trading-fee accrual (USD) per evaluation while a position is open.
# Kept small so portfolio growth is dominated by price moves, not fee drift.
_SIMULATED_FEE_PER_EVAL = 0.01

# --------------------------------------------------------------------------- #
# Minimal Uniswap v3 NonfungiblePositionManager ABI fragments.
# Only the functions/structs the bot uses are declared here.
# --------------------------------------------------------------------------- #
POSITION_MANAGER_MINT_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "token0", "type": "address"},
                    {"name": "token1", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "tickLower", "type": "int24"},
                    {"name": "tickUpper", "type": "int24"},
                    {"name": "amount0Desired", "type": "uint256"},
                    {"name": "amount1Desired", "type": "uint256"},
                    {"name": "amount0Min", "type": "uint256"},
                    {"name": "amount1Min", "type": "uint256"},
                    {"name": "recipient", "type": "address"},
                    {"name": "deadline", "type": "uint256"},
                ],
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "mint",
        "outputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "liquidity", "type": "uint128"},
            {"name": "amount0", "type": "uint256"},
            {"name": "amount1", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function",
    }
]

POSITION_MANAGER_DECREASE_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "liquidity", "type": "uint128"},
                    {"name": "amount0Min", "type": "uint256"},
                    {"name": "amount1Min", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "decreaseLiquidity",
        "outputs": [
            {"name": "amount0", "type": "uint256"},
            {"name": "amount1", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function",
    }
]

POSITION_MANAGER_COLLECT_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amount0Max", "type": "uint128"},
                    {"name": "amount1Max", "type": "uint128"},
                ],
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "collect",
        "outputs": [
            {"name": "amount0", "type": "uint256"},
            {"name": "amount1", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function",
    }
]


class MarketMakerBot:
    """Reactive liquidity provider that trades against ML risk signals.

    The bot is intentionally **stateful**: it remembers whether a position is
    open so it can decide between minting a new one and burning the old one.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.simulation_mode = settings.simulation_mode
        self.tick_spacing = settings.market_maker_tick_spacing
        self.max_range_steps = settings.market_maker_max_range_steps
        self._decimals0 = settings.market_maker_token0_decimals
        self._decimals1 = settings.market_maker_token1_decimals

        # --- Simulated position state ---------------------------------- #
        self.has_active_position: bool = False
        self.current_tick_lower: int = 0
        self.current_tick_upper: int = 0
        self.position_liquidity: int = 0
        self.token_id: int | None = None

        # --- Simulated financial tracking ------------------------------- #
        self._amount0 = settings.market_maker_amount0
        self._amount1 = settings.market_maker_amount1
        self.entry_price: float | None = None  # price when the position opened
        self.accumulated_fees: float = 0.0    # simulated trading fees (USD)
        self.portfolio_history: list[dict[str, Any]] = []
        self._last_price: float | None = None  # most recent market price seen

        # Contract + pool addresses used when building real transactions.
        self._position_manager = settings.uniswap_v3_position_manager
        self._pool = settings.uniswap_v3_pool_eth_usdc

    def state(self) -> dict[str, Any]:
        """Snapshot of the current (simulated) position for the API / UI."""
        current_price = self._last_price
        return {
            "has_active_position": self.has_active_position,
            "tick_lower": self.current_tick_lower,
            "tick_upper": self.current_tick_upper,
            "liquidity": self.position_liquidity,
            "token_id": self.token_id,
            "simulation_mode": self.simulation_mode,
            "tick_spacing": self.tick_spacing,
            "accumulated_fees": self.accumulated_fees,
            "current_impermanent_loss": self.calculate_impermanent_loss(
                current_price
            ),
            "net_portfolio_value": self.calculate_portfolio_value(current_price),
            "sharpe_ratio": self.calculate_sharpe_ratio(),
        }

    # ------------------------------------------------------------------ #
    # Financial performance tracking (simulated P&L)
    # ------------------------------------------------------------------ #
    def _effective_price(self, current_price: float | None) -> float:
        """Resolve a usable token0/token1 price from the best source available."""
        for candidate in (current_price, self._last_price, self.entry_price):
            if candidate is not None and candidate > 0:
                return float(candidate)
        return _FALLBACK_PRICE

    def _hodl_value(self, price: float) -> float:
        """USD value of the deposited assets if simply held at `price`.

        `price` is token0 (USDC) denominated in token1 (WETH). token0 is the
        stablecoin worth $1, so the holding is worth
            amount0 + amount1 / price   (amount1 WETH * USD-per-WETH).
        """
        if price <= 0:
            return float(self._amount0)
        return float(self._amount0 + self._amount1 / price)

    def calculate_impermanent_loss(self, current_price: float | None) -> float:
        """Simulated impermanent loss (USD) versus simply holding the deposit.

        Uses the constant-product AMM formula: when the price moves by
        ``r = current / entry``, an LP position retains ``2*sqrt(r)/(1+r)``
        of the "hodl" value, so the loss is
        ``hodl * (1 - 2*sqrt(r)/(1+r))``. Returns 0 when there is no open
        position or either price is unavailable.
        """
        if (
            not self.has_active_position
            or not self.entry_price
            or self.entry_price <= 0
        ):
            return 0.0
        price = self._effective_price(current_price)
        if price <= 0:
            return 0.0
        ratio = price / self.entry_price
        hodl = self._hodl_value(price)
        lp_ratio = 2.0 * math.sqrt(ratio) / (1.0 + ratio)
        return max(0.0, hodl * (1.0 - lp_ratio))

    def calculate_portfolio_value(self, current_price: float | None) -> float:
        """Simulated net value of the bot's position (USD).

        Equals the current value of the deposited assets ("hodl" baseline)
        plus accumulated trading fees, minus any impermanent loss incurred
        since the position was opened.
        """
        price = self._effective_price(current_price)
        return (
            self._hodl_value(price)
            + self.accumulated_fees
            - self.calculate_impermanent_loss(price)
        )

    def record_portfolio_value(self, current_price: float | None) -> None:
        """Append a (timestamp, net value) snapshot to ``portfolio_history``.

        Called on every evaluation (monitor scan or streamed event). Simulated
        trading fees accrue while a position is open.
        """
        if self.has_active_position:
            self.accumulated_fees += _SIMULATED_FEE_PER_EVAL
        self.portfolio_history.append(
            {
                "timestamp": time.time(),
                "net_portfolio_value": self.calculate_portfolio_value(
                    current_price
                ),
            }
        )

    def _periods_per_year(self) -> float:
        """Estimate samples-per-year from the recorded snapshot timestamps."""
        seconds_per_year = 365.25 * 86400.0
        timestamps = [
            float(p["timestamp"])
            for p in self.portfolio_history
            if isinstance(p.get("timestamp"), (int, float))
            and p["timestamp"] > 0
        ]
        if len(timestamps) >= 2 and timestamps[-1] > timestamps[0]:
            avg_seconds = (timestamps[-1] - timestamps[0]) / (
                len(timestamps) - 1
            )
            if avg_seconds > 0:
                return seconds_per_year / avg_seconds
        return seconds_per_year / max(self._settings.scan_interval_seconds, 1)

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Annualised Sharpe ratio of the recorded portfolio value series.

        Computes period-over-period percentage returns, then annualises using
        the average inter-sample interval. Returns ``0.0`` when there is not
        enough history (fewer than two returns) or the return volatility is
        zero.
        """
        if len(self.portfolio_history) < 3:
            return 0.0

        values = [
            float(p["net_portfolio_value"]) for p in self.portfolio_history
        ]
        returns = [
            (values[i] - values[i - 1]) / values[i - 1]
            for i in range(1, len(values))
            if values[i - 1] != 0.0
        ]
        if len(returns) < 2:
            return 0.0

        arr = np.asarray(returns, dtype=float)
        mean_return = float(np.mean(arr))
        std_return = float(np.std(arr, ddof=1))
        if std_return == 0.0 or not math.isfinite(std_return):
            return 0.0

        periods_per_year = self._periods_per_year()
        risk_free_per_period = risk_free_rate / periods_per_year
        sharpe = (
            (mean_return - risk_free_per_period)
            / std_return
            * math.sqrt(periods_per_year)
        )
        if not math.isfinite(sharpe):
            return 0.0
        return float(sharpe)

    # ------------------------------------------------------------------ #
    # Signal evaluation (the reactive policy)
    # ------------------------------------------------------------------ #
    async def evaluate_signal(
        self, prediction: Any, current_price: float
    ) -> dict[str, Any] | None:
        """React to a new ML prediction.

        Args:
            prediction: a `DrainPrediction` (monitor loop) or the dict returned
                by `LiquidityPredictor.predict` (event stream). Both are
                normalised here, so either shape works.
            current_price: human price of token0 denominated in token1.

        Returns:
            The action taken (or ``None`` when the policy holds the position).
        """
        # Record the latest market price and append a portfolio snapshot on
        # every evaluation (monitor scan or streamed event).
        if current_price and current_price > 0:
            self._last_price = float(current_price)
        self.record_portfolio_value(current_price)

        risk_level, price_impact = self._extract_signal(prediction)
        logger.info(
            "MarketMakerBot evaluating risk=%s impact=%.4f%% active=%s",
            risk_level,
            price_impact,
            self.has_active_position,
        )

        # Protect capital: pull liquidity when risk is elevated.
        if risk_level in {"HIGH", "CRITICAL"} and self.has_active_position:
            return await self.withdraw_liquidity(reason=risk_level)

        # Deploy capital: open a fresh position when the pool looks calm.
        if risk_level == "LOW" and not self.has_active_position:
            return await self.provide_liquidity(current_price, price_impact)

        # Otherwise hold (MEDIUM risk, or already in the right state).
        return None

    @staticmethod
    def _extract_signal(prediction: Any) -> tuple[str, float]:
        """Normalise a prediction (Pydantic model or dict) to (risk, impact)."""
        if isinstance(prediction, dict):
            risk = prediction.get("alert_level") or prediction.get("risk_level")
            impact = prediction.get("price_impact_pct")
            if impact is None:
                impact = prediction.get("predicted_price_impact")
        else:
            risk = getattr(prediction, "alert_level", None) or getattr(
                prediction, "risk_level", None
            )
            impact = getattr(prediction, "price_impact_pct", None)
            if impact is None:
                impact = getattr(prediction, "predicted_price_impact", None)

        risk = str(risk or "LOW").upper()
        try:
            impact = float(impact) if impact is not None else 0.0
        except (TypeError, ValueError):
            impact = 0.0
        return risk, impact

    # ------------------------------------------------------------------ #
    # Tick-range sizing
    # ------------------------------------------------------------------ #
    def calculate_optimal_ticks(
        self, current_price: float, predicted_price_impact: float | None
    ) -> tuple[int, int]:
        """Compute a (tick_lower, tick_upper) range around the current price.

        The range is anchored on the tick nearest `current_price` and widened
        symmetrically. Higher predicted price impact => wider range (capture
        more volatility); lower impact => narrower range (concentrated). The
        result is always snapped to a multiple of the pool's tick spacing.
        """
        impact = abs(float(predicted_price_impact or 0.0))

        # Uniswap's tick is defined on the RAW price ratio (token1/token0 in
        # integer units):  tick = ln(P_raw) / ln(1.0001). `current_price` is the
        # human price, so subtract the decimal-scaling offset
        #   P_raw = P_human * 10^(decimals1 - decimals0).
        center = 0
        if current_price and current_price > 0:
            center = int(
                round(
                    math.log(current_price) / math.log(_TICK_BASE)
                    - (self._decimals0 - self._decimals1)
                    * (math.log(10.0) / math.log(_TICK_BASE))
                )
            )
        center = (center // self.tick_spacing) * self.tick_spacing

        # One step each side at minimum; each +5% of impact adds a step.
        steps = 1 + int(impact / 5.0)
        steps = max(1, min(steps, self.max_range_steps))
        half = steps * self.tick_spacing

        tick_lower = center - half
        tick_upper = center + half
        return tick_lower, tick_upper

    # ------------------------------------------------------------------ #
    # Provide / withdraw
    # ------------------------------------------------------------------ #
    async def provide_liquidity(
        self, current_price: float, predicted_price_impact: float | None = None
    ) -> dict[str, Any]:
        """Open a liquidity position (simulated Mint, or real txn if enabled)."""
        if current_price and current_price > 0:
            self._last_price = float(current_price)
            self.entry_price = float(current_price)

        tick_lower, tick_upper = self.calculate_optimal_ticks(
            current_price, predicted_price_impact
        )

        if self.simulation_mode:
            self.has_active_position = True
            self.current_tick_lower = tick_lower
            self.current_tick_upper = tick_upper
            self.position_liquidity = int(1_000_000)  # placeholder for the sim
            self.token_id = None
            logger.info(
                "[SIMULATION] Mint liquidity in range [%s, %s] "
                "(price=%.8f, impact=%.4f%%)",
                tick_lower,
                tick_upper,
                current_price,
                predicted_price_impact or 0.0,
            )
            return {
                "action": "provide_liquidity",
                "simulated": True,
                "tick_lower": tick_lower,
                "tick_upper": tick_upper,
            }

        # --- Real on-chain execution (requires a configured signer) ----- #
        return await self._send_mint(tick_lower, tick_upper)

    async def withdraw_liquidity(self, reason: str = "MANUAL") -> dict[str, Any]:
        """Close the current position (simulated Burn, or real txn if enabled)."""
        if not self.has_active_position:
            return {"action": "withdraw_liquidity", "skipped": True, "reason": "no_active_position"}

        tick_lower, tick_upper = self.current_tick_lower, self.current_tick_upper

        if self.simulation_mode:
            self.has_active_position = False
            self.current_tick_lower = 0
            self.current_tick_upper = 0
            self.position_liquidity = 0
            self.token_id = None
            self.entry_price = None
            logger.info(
                "[SIMULATION] Burn liquidity in range [%s, %s] (%s)",
                tick_lower,
                tick_upper,
                reason,
            )
            return {
                "action": "withdraw_liquidity",
                "simulated": True,
                "reason": reason,
                "tick_lower": tick_lower,
                "tick_upper": tick_upper,
            }

        # --- Real on-chain execution ----------------------------------- #
        return await self._send_decrease_and_collect(reason)

    # ------------------------------------------------------------------ #
    # Web3 execution boilerplate (real path)
    # ------------------------------------------------------------------ #
    def _w3(self):
        """Lazy read/write Web3 instance bound to the configured HTTP RPC."""
        from web3 import Web3

        return Web3(
            Web3.HTTPProvider(
                self._settings.rpc_url_http,
                request_kwargs={"timeout": self._settings.request_timeout_seconds},
            )
        )

    def _signer(self):
        """Return (account, address) from the configured wallet, or raise."""
        if not self._settings.wallet_private_key or not self._settings.wallet_address:
            raise RuntimeError(
                "Real execution requires WALLET_PRIVATE_KEY and WALLET_ADDRESS "
                "in the environment. Keep SIMULATION_MODE=true for development."
            )
        from web3 import Web3

        account = Web3().eth.account.from_key(self._settings.wallet_private_key)
        return account, self._settings.wallet_address

    def _sign_and_send(self, w3, fn, account, address: str):
        """Build, sign and broadcast a transaction; return the tx hash hex."""
        tx = fn.build_transaction(
            {
                "from": address,
                "nonce": w3.eth.get_transaction_count(address),
                "gas": 1_500_000,
                # Naive EIP-1559 fee strategy — production should use a proper
                # gas oracle. Kept simple because this path is boilerplate.
                "maxFeePerGas": int(w3.eth.gas_price * 2),
                "maxPriorityFeePerGas": int(w3.eth.gas_price // 10),
            }
        )
        signed = account.sign_transaction(tx)
        return w3.eth.send_raw_transaction(signed.raw_transaction).hex()

    async def _send_mint(self, tick_lower: int, tick_upper: int) -> dict[str, Any]:
        """Build/sign/broadcast a NonfungiblePositionManager.mint() call."""
        from web3 import Web3

        w3 = self._w3()
        account, address = self._signer()
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(self._position_manager),
            abi=POSITION_MANAGER_MINT_ABI,
        )

        amount0 = int(self._settings.market_maker_amount0 * 10**6)  # USDC (6 dp)
        amount1 = int(self._settings.market_maker_amount1 * 10**18)  # WETH (18 dp)
        deadline = w3.eth.get_block("latest")["timestamp"] + 300

        fn = contract.functions.mint(
            (
                self._pool,
                self._pool,
                3000,
                tick_lower,
                tick_upper,
                amount0,
                amount1,
                0,  # amount0Min (slippage protection)
                0,  # amount1Min
                address,
                deadline,
            )
        )
        tx_hash = self._sign_and_send(w3, fn, account, address)

        self.has_active_position = True
        self.current_tick_lower = tick_lower
        self.current_tick_upper = tick_upper
        return {"action": "provide_liquidity", "simulated": False, "tx_hash": tx_hash}

    async def _send_decrease_and_collect(self, reason: str) -> dict[str, Any]:
        """Burn: decreaseLiquidity() then collect() the freed tokens."""
        from web3 import Web3

        w3 = self._w3()
        account, address = self._signer()
        deadline = w3.eth.get_block("latest")["timestamp"] + 300
        token_id = self.token_id or 0

        decrease_contract = w3.eth.contract(
            address=Web3.to_checksum_address(self._position_manager),
            abi=POSITION_MANAGER_DECREASE_ABI,
        )
        fn = decrease_contract.functions.decreaseLiquidity(
            (token_id, 0, 0, 0, deadline)  # liquidity=0 => remove all
        )
        tx_hash = self._sign_and_send(w3, fn, account, address)

        collect_contract = w3.eth.contract(
            address=Web3.to_checksum_address(self._position_manager),
            abi=POSITION_MANAGER_COLLECT_ABI,
        )
        collect_fn = collect_contract.functions.collect(
            (token_id, address, 2**128 - 1, 2**128 - 1)
        )
        collect_hash = self._sign_and_send(w3, collect_fn, account, address)

        self.has_active_position = False
        self.current_tick_lower = 0
        self.current_tick_upper = 0
        self.entry_price = None
        return {
            "action": "withdraw_liquidity",
            "simulated": False,
            "reason": reason,
            "decrease_tx": tx_hash,
            "collect_tx": collect_hash,
        }
