"""Central configuration for the crypto price forecast pipeline."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

# Supported tickers (normalised key -> yfinance symbol).
TICKERS: dict[str, str] = {
    "btc": "BTC-USD",
    "eth": "ETH-USD",
}

# Macro / equity series via yfinance (used when no FRED key is provided).
YFINANCE_SERIES: dict[str, str] = {
    "sp500_close": "^GSPC",  # S&P 500 index
    "dxy": "DX-Y.NYB",       # US Dollar Index (ICE futures)
    "gold": "GC=F",          # Gold futures (continuous contract)
    "treasury_10y": "^TNX",  # 10-Year Treasury yield (quoted as yield x 10)
}

# Macro series via FRED (used when FRED_API_KEY is set).
FRED_SERIES: dict[str, str] = {
    "dxy": "DTWEXBGS",            # Nominal Broad U.S. Dollar Index
    "gold": "GOLDPMGBD228NLBM",   # Gold Fixing Price, London (USD/oz)
    "treasury_10y": "DGS10",      # 10-Year Treasury Constant Maturity Rate (%)
}

# Geopolitical Risk (GPR) index — daily CSV hosted by the authors.
GPR_URLS: list[str] = [
    "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.csv",
    "https://www.matteoiacoviello.com/gpr_files/gpr_daily_recent.csv",
]

# Model input features (order matters; persisted with the model).
FEATURE_COLUMNS: list[str] = [
    "open", "high", "low", "close", "volume",
    "sp500_close", "dxy", "gold", "treasury_10y", "gpr",
]

TARGET_TYPE: str = os.getenv("TARGET_TYPE", "regression")
TRAIN_SPLIT: float = 0.8  # chronological 80/20 split (no shuffle)
SEED: int = 42
