"""Data sourcing: crypto (yfinance), macro (FRED or yfinance), GPR (hosted CSV)."""
from __future__ import annotations

import logging
import os
import time

import pandas as pd

from config import (
    DATA_DIR,
    FRED_SERIES,
    GPR_URLS,
    TICKERS,
    YFINANCE_SERIES,
)

logger = logging.getLogger(__name__)


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance sometimes returns a MultiIndex for columns; normalise it."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _normalize_index(series: pd.Series) -> pd.Series:
    series.index = pd.to_datetime(series.index, errors="coerce").tz_localize(None)
    series = series[~series.index.isna()]
    series = series[~series.index.duplicated(keep="last")]
    return series.sort_index()


def fetch_crypto(symbol: str, period: str = "4y") -> pd.DataFrame:
    """Daily OHLCV for a crypto symbol."""
    import yfinance as yf

    raw = yf.download(
        symbol, period=period, interval="1d", auto_adjust=True, progress=False
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol}")

    df = _flatten_columns(raw)[["Open", "High", "Low", "Close", "Volume"]]
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index = pd.to_datetime(df.index, errors="coerce").tz_localize(None)
    return df.sort_index()


def fetch_yfinance_series(symbol: str, period: str = "4y") -> pd.Series:
    """Daily closing price for a single yfinance symbol."""
    import yfinance as yf

    raw = yf.download(
        symbol, period=period, interval="1d", auto_adjust=True, progress=False
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol}")

    df = _flatten_columns(raw)
    close = df["Close"].squeeze()
    close = close.rename(symbol)
    return _normalize_index(close)


def fetch_fred_series(series_id: str, api_key: str) -> pd.Series:
    """Daily series from the FRED API (no extra dependency)."""
    import requests

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])

    index = pd.to_datetime([o["date"] for o in observations], errors="coerce")
    values = pd.to_numeric([o["value"] for o in observations], errors="coerce")
    series = pd.Series(values, index=index).rename(series_id)
    return _normalize_index(series)


def fetch_gpr() -> pd.Series:
    """Geopolitical Risk (GPR) index from the authors' hosted data.

    The authors publish the daily series as an Excel workbook; older CSV
    endpoints are kept as a fallback.
    """
    xls_url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
    try:
        df = pd.read_excel(xls_url)
        date_col = df.columns[0]
        value_col = (
            "GPRD"
            if "GPRD" in df.columns
            else [c for c in df.columns if c.lower().startswith("gpr")][0]
        )
        series = pd.to_numeric(df[value_col], errors="coerce")
        series.index = pd.to_datetime(df[date_col], errors="coerce")
        series = _normalize_index(series).rename("gpr")
        if not series.empty:
            return series
    except Exception as exc:  # noqa: BLE001
        logger.warning("GPR Excel download failed from %s: %s", xls_url, exc)

    for url in GPR_URLS:
        try:
            df = pd.read_csv(url)
            date_col = df.columns[0]
            value_col = (
                "GPRD"
                if "GPRD" in df.columns
                else [c for c in df.columns if c.lower().startswith("gpr")][0]
            )
            series = pd.to_numeric(df[value_col], errors="coerce")
            series.index = pd.to_datetime(df[date_col], errors="coerce")
            series = _normalize_index(series).rename("gpr")
            return series
        except Exception as exc:  # noqa: BLE001
            logger.warning("GPR download failed from %s: %s", url, exc)
    raise RuntimeError("Could not download the GPR index from any source.")


def _fetch_macro(name: str) -> pd.Series:
    """Fetch a macro series, preferring FRED when a key is available."""
    api_key = os.getenv("FRED_API_KEY")
    if name == "sp500_close":
        return fetch_yfinance_series(YFINANCE_SERIES[name]).rename(name)

    if api_key:
        return fetch_fred_series(FRED_SERIES[name], api_key).rename(name)

    # yfinance fallback
    series = fetch_yfinance_series(YFINANCE_SERIES[name]).rename(name)
    if name == "treasury_10y":
        # ^TNX is quoted as yield x 10 (e.g. 42.5 = 4.25%).
        series = series / 10.0
    return series


def fetch_all(ticker: str = "btc", cache: bool = True) -> pd.DataFrame:
    """Build the aligned raw DataFrame (crypto OHLCV + macro + GPR)."""
    symbol = TICKERS[ticker]
    cache_path = DATA_DIR / f"{ticker}_raw.csv"

    if cache and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 86400:  # cache valid for one day
            logger.info("Loading cached raw data from %s", cache_path)
            raw = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return raw

    crypto = fetch_crypto(symbol)
    series = {
        "sp500_close": _fetch_macro("sp500_close"),
        "dxy": _fetch_macro("dxy"),
        "gold": _fetch_macro("gold"),
        "treasury_10y": _fetch_macro("treasury_10y"),
        "gpr": fetch_gpr(),
    }

    raw = pd.concat([crypto, *series.values()], axis=1)
    raw = raw.sort_index()

    # Forward-fill weekend / holiday gaps in traditional market indicators
    # (crypto trades 7 days a week, so its columns have no weekend gaps).
    raw = raw.ffill()
    raw = raw.dropna(subset=["close"])  # crypto close must exist

    if cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        raw.to_csv(cache_path)

    return raw
