"""Pool data providers.

`OnChainPoolProvider` reads live Uniswap v3 state via Web3.py.
`MockPoolProvider` synthesises realistic data so the app runs offline.
"""
from __future__ import annotations

import abc
import hashlib
import math
import random
import time

from web3 import Web3

from ..core.config import Settings
from ..schemas.pool import PoolState, TokenMeta
from .price_impact import Q96, STABLES, human_price
from .web3_client import Web3Client

POOL_ABI = [
    "function token0() view returns (address)",
    "function token1() view returns (address)",
    "function fee() view returns (uint24)",
    "function liquidity() view returns (uint128)",
    "function slot0() view returns (uint160 sqrtPriceX96, int24 tick, "
    "uint16 observationIndex, uint16 observationCardinality, "
    "uint16 observationCardinalityNext, uint8 feeProtocol, bool unlocked)",
]

ERC20_ABI = [
    "function symbol() view returns (string)",
    "function decimals() view returns (uint8)",
]

# Symbol -> decimals for the assets used in the default watchlist / mock mode.
_DECIMALS = {"USDC": 6, "USDT": 6, "DAI": 18, "WETH": 18, "WBTC": 8}


class PoolProvider(abc.ABC):
    @abc.abstractmethod
    def get_pool_state(self, entry: dict) -> PoolState:
        """Return the current on-chain (or simulated) state of a pool."""


class OnChainPoolProvider(PoolProvider):
    def __init__(self, settings: Settings, web3_client: Web3Client) -> None:
        self._settings = settings
        self._client = web3_client
        self._token_cache: dict[str, TokenMeta] = {}

    def get_pool_state(self, entry: dict) -> PoolState:
        w3 = self._client.ensure_connected()
        address = self._client.validate_address(entry["address"])

        pool = w3.eth.contract(address=w3.to_checksum_address(address), abi=POOL_ABI)
        token0_addr = pool.functions.token0().call()
        token1_addr = pool.functions.token1().call()
        fee = int(pool.functions.fee().call())
        liquidity = int(pool.functions.liquidity().call())
        slot0 = pool.functions.slot0().call()
        sqrt_price_x96 = int(slot0[0])
        tick = int(slot0[1])

        token0 = self._get_token(token0_addr)
        token1 = self._get_token(token1_addr)
        price = human_price(sqrt_price_x96, token0.decimals, token1.decimals)

        return PoolState(
            address=address,
            token0=token0,
            token1=token1,
            fee=fee,
            liquidity=liquidity,
            sqrt_price_x96=sqrt_price_x96,
            tick=tick,
            price=price,
            timestamp=int(time.time()),
        )

    def _get_token(self, address: str) -> TokenMeta:
        addr = self._client.validate_address(address)
        if addr in self._token_cache:
            return self._token_cache[addr]

        w3 = self._client.ensure_connected()
        token = w3.eth.contract(address=w3.to_checksum_address(addr), abi=ERC20_ABI)
        try:
            symbol = token.functions.symbol().call()
        except Exception:  # noqa: BLE001 - some tokens lack `symbol`
            symbol = addr[:6]
        try:
            decimals = int(token.functions.decimals().call())
        except Exception:  # noqa: BLE001
            decimals = 18

        meta = TokenMeta(address=addr, symbol=symbol or "???", decimals=decimals)
        self._token_cache[addr] = meta
        return meta


class MockPoolProvider(PoolProvider):
    """Deterministic-ish synthetic data with liquidity-drain events."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tokens: dict[str, tuple[TokenMeta, TokenMeta]] = {}
        self._rngs: dict[str, random.Random] = {}
        self._prices: dict[str, float] = {}
        self._liquidity: dict[str, int] = {}
        self._seed()

    def _seed(self) -> None:
        for entry in self._settings.watchlist:
            key = entry["address"].lower()
            t0 = self._meta(entry["token0"])
            t1 = self._meta(entry["token1"])
            self._tokens[key] = (t0, t1)
            self._rngs[key] = random.Random(entry["address"])
            self._prices[key] = float(entry.get("price", 1.0))
            self._liquidity[key] = self._base_liquidity(entry)

    @staticmethod
    def _meta(symbol: str) -> TokenMeta:
        decimals = _DECIMALS.get(symbol.upper(), 18)
        return TokenMeta(address=MockPoolProvider._fake_address(symbol), symbol=symbol, decimals=decimals)

    @staticmethod
    def _fake_address(symbol: str) -> str:
        digest = hashlib.sha256(symbol.encode()).hexdigest()
        return Web3.to_checksum_address("0x" + digest[:40])

    def _base_liquidity(self, entry: dict) -> int:
        """Derive a realistic raw liquidity from a target USD notional per side."""
        t0, t1 = entry["token0"], entry["token1"]
        d0 = _DECIMALS.get(t0.upper(), 18)
        d1 = _DECIMALS.get(t1.upper(), 18)
        price = float(entry.get("price", 1.0))
        target_usd = 50_000_000.0

        if t1.upper() in STABLES:
            p0_usd, p1_usd = price, 1.0
        elif t0.upper() in STABLES:
            p0_usd, p1_usd = 1.0, (1.0 / price) if price else 1.0
        else:
            p0_usd, p1_usd = price, 1.0

        x_raw = (target_usd / p0_usd) * (10**d0)
        y_raw = (target_usd / p1_usd) * (10**d1)
        liquidity = math.sqrt(x_raw * y_raw)

        seed = int(hashlib.sha256(entry["address"].encode()).hexdigest()[:8], 16)
        jitter = 0.8 + (seed % 400) / 1000.0  # 0.8 .. 1.2
        return int(liquidity * jitter)

    def get_pool_state(self, entry: dict) -> PoolState:
        key = entry["address"].lower()
        token0, token1 = self._tokens[key]
        rng = self._rngs[key]

        # Price: small random walk around the seed price.
        price = self._prices[key] * (1.0 + rng.gauss(0.0, 0.002))
        price = max(price, 1e-12)
        self._prices[key] = price

        # Liquidity: mild decay plus occasional sharp drain events.
        liquidity = self._liquidity[key]
        if rng.random() < 0.03:
            liquidity *= 1.0 - rng.uniform(0.05, 0.25)
        else:
            liquidity *= 1.0 + rng.gauss(-0.001, 0.003)
        liquidity = max(int(liquidity), 1)
        self._liquidity[key] = liquidity

        raw_price = price / (10 ** (token0.decimals - token1.decimals))
        sqrt_price_x96 = int(math.sqrt(raw_price) * Q96) if raw_price > 0 else 0
        tick = int(round(math.log(raw_price) / math.log(1.0001))) if raw_price > 0 else 0

        return PoolState(
            address=entry["address"],
            token0=token0,
            token1=token1,
            fee=int(entry.get("fee", 3000)),
            liquidity=liquidity,
            sqrt_price_x96=sqrt_price_x96,
            tick=tick,
            price=price,
            timestamp=int(time.time()),
        )


def build_pool_provider(settings: Settings, web3_client: Web3Client) -> PoolProvider:
    if settings.mock_mode:
        return MockPoolProvider(settings)
    return OnChainPoolProvider(settings, web3_client)
