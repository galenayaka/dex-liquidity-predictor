"""Async Uniswap v3 on-chain event listener.

Subscribes to `Swap` and `Burn` events for a single liquidity pool over a
WebSocket RPC and forwards every new event to connected WebSocket clients.

In mock mode a synthetic generator emits the same payload shape so the
pipeline can be developed and demoed without a node.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

from web3 import AsyncWeb3, Web3

from ..core.config import Settings
from ..db.crud import save_metrics_to_db
from ..services.liquidity_predictor import LiquidityPredictor
from ..websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)

# Canonical event signatures (topic0).
SWAP_SIGNATURE = "Swap(address,address,int256,int256,uint160,uint128,int24)"
BURN_SIGNATURE = "Burn(address,int24,int24,uint128,uint256,uint256)"
SWAP_TOPIC = Web3.keccak(text=SWAP_SIGNATURE).hex()
BURN_TOPIC = Web3.keccak(text=BURN_SIGNATURE).hex()

EVENTS_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "name": "Swap",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "recipient", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "int256"},
            {"indexed": False, "name": "amount1", "type": "int256"},
            {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": False, "name": "liquidity", "type": "uint128"},
            {"indexed": False, "name": "tick", "type": "int24"},
        ],
    },
    {
        "anonymous": False,
        "name": "Burn",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": False, "name": "tickLower", "type": "int24"},
            {"indexed": False, "name": "tickUpper", "type": "int24"},
            {"indexed": False, "name": "amount", "type": "uint128"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
    },
]

# Above this magnitude integers are sent as strings so JS clients keep precision.
_JSON_MAX_INT = 2**53


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, int) and abs(value) > _JSON_MAX_INT:
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


def _topic_to_event(topic: str) -> str | None:
    if topic == SWAP_TOPIC:
        return "Swap"
    if topic == BURN_TOPIC:
        return "Burn"
    return None


_Q96 = 2**96


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class UniswapV3EventListener:
    def __init__(
        self,
        settings: Settings,
        ws_manager: ConnectionManager,
        predictor: LiquidityPredictor,
    ) -> None:
        self._settings = settings
        self._ws = ws_manager
        self._predictor = predictor
        self._stop = asyncio.Event()
        # Notional USD depth, updated on each Swap and reused for Burn events.
        self._last_depth_usd: float = 50_000_000.0
        # Last implied WETH-side reserve (token B), reused for Burn events.
        self._last_token_b_reserve: float | None = None
        # Cached gas price (wei) to avoid an RPC round-trip per event.
        self._gas_price: int = 0
        self._gas_price_ts: float = 0.0

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        if self._settings.mock_mode:
            await self._run_mock()
        else:
            await self._run_onchain()

    # ------------------------------------------------------------------ #
    # On-chain (real) listener
    # ------------------------------------------------------------------ #
    async def _run_onchain(self) -> None:
        pool = self._settings.uniswap_v3_pool_eth_usdc
        try:
            from web3.providers.persistent import WebSocketProvider

            w3 = AsyncWeb3(WebSocketProvider(endpoint_uri=self._settings.rpc_url_ws))
            subscription_id = await w3.eth.subscribe(
                "logs",
                {"address": pool, "topics": [[SWAP_TOPIC, BURN_TOPIC]]},
            )
            logger.info(
                "Subscribed to Swap/Burn on %s (subscription %s)",
                pool,
                subscription_id,
            )
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(pool), abi=EVENTS_ABI
            )
            async for message in w3.socket.process_subscriptions():
                if self._stop.is_set():
                    break
                if message.get("subscription") != subscription_id:
                    continue
                log = message.get("result")
                if log:
                    await self._refresh_gas_price(w3)
                    await self._handle_log(contract, log)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Event subscription terminated: %s", exc)

    async def _refresh_gas_price(self, w3: AsyncWeb3) -> None:
        now = time.time()
        if now - self._gas_price_ts > 15.0:
            try:
                self._gas_price = int(await w3.eth.gas_price)
                self._gas_price_ts = now
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to fetch gas price: %s", exc)

    async def _handle_log(self, contract: Any, log: dict[str, Any]) -> None:
        topics = log.get("topics") or []
        if not topics:
            return

        event_name = _topic_to_event(topics[0])
        if event_name is None:
            return

        try:
            event = getattr(contract.events, event_name)
            decoded = event.process_log(log)
            args = decoded.get("args", {}) if isinstance(decoded, dict) else {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to decode %s log: %s", event_name, exc)
            return

        result = self._run_prediction(event_name, args, self._gas_price)
        self._save_metric(result)
        await self._broadcast_event(event_name, log, args, result["prediction"])

    async def _broadcast_event(
        self,
        event_name: str,
        log: dict[str, Any],
        args: dict[str, Any],
        prediction: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "type": "event",
            "event": event_name,
            "pool": self._settings.uniswap_v3_pool_eth_usdc,
            "pair": self._settings.uniswap_v3_pool_pair,
            "transaction_hash": log.get("transactionHash"),
            "block_number": log.get("blockNumber"),
            "args": _to_jsonable(args),
            "prediction": prediction,
            "raw": {
                "topics": log.get("topics"),
                "data": log.get("data"),
                "log_index": log.get("logIndex"),
            },
            "timestamp": int(time.time()),
        }
        await self._ws.broadcast(payload)
        logger.info(
            "Broadcast %s on %s (tx %s) -> %s",
            event_name,
            self._settings.uniswap_v3_pool_pair,
            log.get("transactionHash"),
            prediction,
        )

    def _run_prediction(
        self, event_name: str, args: dict[str, Any], gas_price: int
    ) -> dict[str, Any]:
        """Run inference and return the prediction plus the metric inputs."""
        if event_name == "Swap":
            amount0 = abs(_as_int(args.get("amount0", 0)))
            liquidity = _as_int(args.get("liquidity", 0))
            sqrt_price_x96 = _as_int(args.get("sqrtPriceX96", 0))

            # token0 of the watched pool is USDC (6 decimals) -> USD-equivalent.
            swap_volume = amount0 / 1e6
            token_b_reserve: float | None = None
            if sqrt_price_x96 > 0 and liquidity > 0:
                sqrt_raw = sqrt_price_x96 / _Q96
                # Implied reserves from current price + in-range liquidity:
                # token A (USDC) and token B (WETH), in human units.
                self._last_depth_usd = liquidity / sqrt_raw / 1e6
                token_b_reserve = liquidity * sqrt_raw / 1e18
                self._last_token_b_reserve = token_b_reserve
            reserve_depth = self._last_depth_usd
            token_a_reserve = reserve_depth
            context = {"event": "Swap", "liquidity_change_pct": 0.0}
        else:  # Burn
            amount0 = abs(_as_int(args.get("amount0", 0)))
            swap_volume = amount0 / 1e6
            reserve_depth = self._last_depth_usd
            token_a_reserve = reserve_depth
            token_b_reserve = self._last_token_b_reserve
            context = {"event": "Burn", "liquidity_change_pct": None}

        prediction = self._predictor.predict(
            swap_volume=swap_volume,
            reserve_depth=reserve_depth,
            gas_price=float(gas_price),
            context=context,
        )

        return {
            "prediction": prediction,
            "swap_volume": swap_volume,
            "token_a_reserve": token_a_reserve,
            "token_b_reserve": token_b_reserve,
        }

    def _save_metric(self, result: dict[str, Any]) -> None:
        """Persist one metric row right after inference (before broadcast)."""
        prediction = result["prediction"]
        save_metrics_to_db(
            pool_address=self._settings.uniswap_v3_pool_eth_usdc,
            time=datetime.now(timezone.utc),
            token_a_reserve=result["token_a_reserve"],
            token_b_reserve=result["token_b_reserve"],
            swap_volume=result["swap_volume"],
            predicted_drain=prediction["predicted_drain_percentage"],
            predicted_price_impact=prediction["predicted_price_impact"],
        )

    # ------------------------------------------------------------------ #
    # Mock listener (offline development)
    # ------------------------------------------------------------------ #
    async def _run_mock(self) -> None:
        rng = random.Random(7)
        # sqrtPriceX96 for USDC/WETH at ~1 USDC = 0.0003 WETH.
        base_sqrt_price = 1_372_000_000_000_000_000_000_000_000_000_000

        while not self._stop.is_set():
            await asyncio.sleep(rng.uniform(2.0, 6.0))
            kind = rng.choice(["Swap", "Swap", "Burn"])
            tx_hash = "0x" + "%064x" % rng.getrandbits(256)

            # Gas price in wei (20..200 gwei).
            gas_price = rng.randint(20, 200) * 10**9

            if kind == "Swap":
                # amount0 is USDC (6 dp): $100 .. $1M notional.
                amount0 = rng.choice([-1, 1]) * rng.randint(10**8, 10**12)
                args = {
                    "sender": self._fake_address(rng),
                    "recipient": self._fake_address(rng),
                    "amount0": amount0,
                    "amount1": -int(amount0 * 3e8),
                    "sqrtPriceX96": int(base_sqrt_price * rng.uniform(0.999, 1.001)),
                    "liquidity": rng.randint(5 * 10**16, 2 * 10**18),
                    "tick": rng.randint(-200_000, -195_000),
                }
            else:
                args = {
                    "owner": self._fake_address(rng),
                    "tickLower": rng.randint(-210_000, -200_000),
                    "tickUpper": rng.randint(-190_000, -180_000),
                    "amount": rng.randint(10**15, 10**17),
                    "amount0": rng.randint(10**8, 10**12),
                    "amount1": rng.randint(10**17, 10**20),
                }

            log = {
                "transactionHash": tx_hash,
                "blockNumber": rng.randint(19_000_000, 20_000_000),
                "topics": [SWAP_TOPIC if kind == "Swap" else BURN_TOPIC],
                "data": "0x",
                "logIndex": rng.randint(0, 200),
            }
            result = self._run_prediction(kind, args, gas_price)
            self._save_metric(result)
            await self._broadcast_event(kind, log, args, result["prediction"])

    @staticmethod
    def _fake_address(rng: random.Random) -> str:
        return Web3.to_checksum_address("0x" + "%040x" % rng.getrandbits(160))
