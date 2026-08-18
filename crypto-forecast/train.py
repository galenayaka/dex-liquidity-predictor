"""End-to-end training entrypoint: fetch -> features -> train -> save to registry.

Examples:
    python train.py --ticker btc
    python train.py --all
"""
from __future__ import annotations

import argparse
import logging

from config import TICKERS
from data_source import fetch_all
from features import build_dataset
from model import save_model, train

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def train_one(ticker: str) -> None:
    logger.info("Fetching data for %s (%s)…", ticker, TICKERS[ticker]["name"])
    raw = fetch_all(ticker)

    df, features = build_dataset(raw, "regression")
    logger.info("Dataset ready: %d rows, %d features", len(df), len(features))
    logger.info("Date range: %s -> %s", df.index.min().date(), df.index.max().date())

    model, metrics, _ = train(df, features)
    save_model(ticker, model, features, metrics)

    logger.info("Evaluation on held-out test set (median prediction):")
    for name, value in metrics.items():
        logger.info("  %s = %.4f", name, value)
    logger.info("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the crypto price forecast model registry")
    parser.add_argument("--ticker", default=None, choices=sorted(TICKERS), help="Train one ticker")
    parser.add_argument("--all", action="store_true", help="Train every registered ticker")
    args = parser.parse_args()

    tickers = sorted(TICKERS) if (args.all or not args.ticker) else [args.ticker]
    for ticker in tickers:
        try:
            train_one(ticker)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to train %s: %s", ticker, exc)


if __name__ == "__main__":
    main()
