"""End-to-end training entrypoint: fetch -> features -> train -> evaluate -> save.

Examples:
    python train.py --ticker btc
    python train.py --ticker eth --target classification
"""
from __future__ import annotations

import argparse
import logging

from config import TARGET_TYPE, TICKERS
from data_source import fetch_all
from features import build_dataset
from model import save_model, train

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the crypto price forecast model")
    parser.add_argument("--ticker", default="btc", choices=sorted(TICKERS))
    parser.add_argument("--target", default=TARGET_TYPE, choices=["regression", "classification"])
    parser.add_argument("--no-ensemble", action="store_true", help="Use plain XGBoost instead of the ensemble")
    args = parser.parse_args()

    logger.info("Fetching data for %s (%s)…", args.ticker, TICKERS[args.ticker])
    raw = fetch_all(args.ticker)

    df, features = build_dataset(raw, args.target)
    logger.info("Dataset ready: %d rows, %d features", len(df), len(features))
    logger.info("Date range: %s -> %s", df.index.min().date(), df.index.max().date())

    model, metrics, _ = train(df, features, args.target, ensemble=not args.no_ensemble)
    save_model(model, features, args.target, args.ticker)

    logger.info("Evaluation on held-out test set:")
    for name, value in metrics.items():
        if name == "classification_report":
            continue
        logger.info("  %s = %.4f", name, value)
    logger.info("Done.")


if __name__ == "__main__":
    main()
