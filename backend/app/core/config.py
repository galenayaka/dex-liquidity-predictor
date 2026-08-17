"""Application settings loaded from the environment / `.env` file."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------- #
    app_name: str = "Predictive Liquidity & Price Impact Analytics Dashboard"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Database ------------------------------------------------------- #
    # PostgreSQL connection URL for SQLAlchemy 2.0 (psycopg driver).
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/dex_predictor"
    )

    # --- Web3 ----------------------------------------------------------- #
    # When True the backend runs fully offline against synthetic data.
    mock_mode: bool = True
    rpc_url_http: str = "https://eth-mainnet.g.alchemy.com/v2/your-api-key"
    rpc_url_ws: str = "wss://eth-mainnet.g.alchemy.com/v2/your-api-key"
    chain_id: int = 1
    request_timeout_seconds: int = 15

    # --- Uniswap v3 (Ethereum mainnet) ---------------------------------- #
    uniswap_v3_factory: str = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    uniswap_v3_router: str = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    uniswap_v3_position_manager: str = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
    # Pool watched by the Swap/Burn event listener (USDC/WETH 0.3%).
    uniswap_v3_pool_eth_usdc: str = "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8"
    uniswap_v3_pool_pair: str = "ETH/USDC"

    # --- Monitoring ----------------------------------------------------- #
    scan_interval_seconds: int = 30
    liquidity_drain_threshold: float = -0.15
    price_impact_alert_threshold: float = 0.03
    sample_history_size: int = 180
    model_path: str = "models/liquidity_drain_model.json"
    # Optional .pkl model used by LiquidityPredictor for the live event stream.
    liquidity_model_path: str = "models/liquidity_predictor.pkl"

    # --- Watchlist ------------------------------------------------------ #
    # Each entry: address, token0/token1 symbols and (for mock mode) an
    # approximate human price of token0 denominated in token1.
    watchlist: list[dict[str, Any]] = [
        {"address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640", "token0": "USDC", "token1": "WETH", "fee": 500, "price": 0.00030},
        {"address": "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8", "token0": "USDC", "token1": "WETH", "fee": 3000, "price": 0.00030},
        {"address": "0x99ac8cA7087fA4A2A1FB6357269965A2014ABc35", "token0": "WBTC", "token1": "USDC", "fee": 3000, "price": 60000.0},
        {"address": "0x5777d92f208679DB4b9778590Fa3CAB3aC9e2168", "token0": "DAI", "token1": "USDC", "fee": 100, "price": 1.0},
        {"address": "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36", "token0": "WETH", "token1": "USDT", "fee": 3000, "price": 3000.0},
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("watchlist", mode="before")
    @classmethod
    def _parse_watchlist(cls, value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
