"""Dependency-injection container.

Lazy singletons shared by the REST layer, the monitor task and the WebSocket
endpoint. Kept free of FastAPI imports so any module can use them.
"""
from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from ..ml.predictor import DrainPredictor
from ..services.liquidity_predictor import LiquidityPredictor
from ..services.market_maker import MarketMakerBot
from ..services.mempool import MempoolWatcher
from ..services.pool_provider import build_pool_provider
from ..services.price_impact import PriceImpactService
from ..services.store import SnapshotStore
from ..services.uniswap_events import UniswapV3EventListener
from ..services.web3_client import Web3Client
from ..websocket.manager import ConnectionManager


@lru_cache
def get_web3_client() -> Web3Client:
    return Web3Client(get_settings())


@lru_cache
def get_pool_provider():
    return build_pool_provider(get_settings(), get_web3_client())


@lru_cache
def get_price_impact_service() -> PriceImpactService:
    return PriceImpactService()


@lru_cache
def get_store() -> SnapshotStore:
    return SnapshotStore()


@lru_cache
def get_ws_manager() -> ConnectionManager:
    return ConnectionManager()


@lru_cache
def get_predictor() -> DrainPredictor:
    return DrainPredictor(get_settings())


@lru_cache
def get_mempool_watcher() -> MempoolWatcher:
    return MempoolWatcher(get_settings())


@lru_cache
def get_liquidity_predictor() -> LiquidityPredictor:
    return LiquidityPredictor(get_settings().liquidity_model_path)


@lru_cache
def get_market_maker_bot() -> MarketMakerBot:
    return MarketMakerBot(get_settings())


@lru_cache
def get_event_listener() -> UniswapV3EventListener:
    return UniswapV3EventListener(
        get_settings(),
        get_ws_manager(),
        get_liquidity_predictor(),
        get_market_maker_bot(),
    )
