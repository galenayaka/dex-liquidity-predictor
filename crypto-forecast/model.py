"""Model training, evaluation and persistence (quantile XGBoost registry)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import FEATURE_COLUMNS, MODEL_DIR, SEED, TRAIN_SPLIT

logger = logging.getLogger(__name__)

QUANTILES = [0.025, 0.5, 0.975]  # lower bound / median / upper bound


def model_file(ticker: str) -> Path:
    """Registry path for a ticker's XGBoost weights, e.g. models/BTC_xgb.json."""
    return MODEL_DIR / f"{ticker.upper()}_xgb.json"


def meta_file(ticker: str) -> Path:
    """Registry path for a ticker's metadata (features, metrics, …)."""
    return MODEL_DIR / f"{ticker.upper()}_meta.json"


def chronological_split(df: pd.DataFrame, split: float = TRAIN_SPLIT) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Time-ordered split (no shuffle) to prevent look-ahead bias."""
    cut = int(len(df) * split)
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


def build_model():
    """Quantile XGBoost: predicts a median plus lower/upper 95% bounds."""
    return xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=QUANTILES,
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=SEED,
        tree_method="hist",
    )


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Regression metrics for the median prediction."""
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def train(
    df: pd.DataFrame,
    features: list[str],
) -> tuple[Any, dict[str, Any], pd.DataFrame]:
    """Train on the chronological train split and evaluate on the test split."""
    train_df, test_df = chronological_split(df)
    X_train, y_train = train_df[features], train_df["target"]
    X_test, y_test = test_df[features], test_df["target"]

    model = build_model()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)  # shape (n, 3): [q025, median, q975]
    median = preds[:, 1]

    metrics = evaluate(y_test.to_numpy(), median)

    results = test_df[["close", "target"]].copy()
    results["prediction"] = median
    return model, metrics, results


def save_model(
    ticker: str,
    model: Any,
    features: list[str],
    metrics: dict[str, Any] | None = None,
) -> None:
    """Persist the XGBoost model (.json) + metadata to the registry."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_file(ticker)))
    meta = {
        "ticker": ticker,
        "features": features,
        "target_type": "regression",
        "metrics": metrics or {},
    }
    meta_file(ticker).write_text(json.dumps(meta, indent=2))
    logger.info("Saved %s", model_file(ticker))


def predict_with_uncertainty(
    booster: Any, row: pd.DataFrame, meta: dict[str, Any]
) -> dict[str, Any]:
    """Median point forecast + 95% interval (ŷ ± 1.96·RMSE) + confidence."""
    dmat = xgb.DMatrix(row[meta["features"]])
    q = booster.predict(dmat)  # shape (1, 3): [q025, median, q975]
    median = float(q[0][1])

    metrics: dict[str, Any] = meta.get("metrics", {})
    rmse = metrics.get("rmse")

    if rmse and rmse > 0:
        # Standard normal 95% band around the median point estimate.
        interval_low = median - 1.96 * rmse
        interval_high = median + 1.96 * rmse
        # Confidence: how tight that band is relative to the price level.
        confidence = (
            max(0.0, min(100.0, 100.0 * (1.0 - (1.96 * rmse) / median)))
            if median > 0
            else None
        )
    else:
        # Fallback: use the quantile bounds, clamped to stay monotonic.
        low = float(q[0][0])
        high = float(q[0][2])
        interval_low = min(low, median)
        interval_high = max(median, high)
        width = interval_high - interval_low
        confidence = (
            max(0.0, min(100.0, 100.0 * (1.0 - (width / 2.0) / median)))
            if median > 0
            else None
        )

    return {
        "ticker": meta.get("ticker"),
        "target_type": "regression",
        "predicted_price": median,
        "confidence": round(confidence, 1) if confidence is not None else None,
        "interval_low": round(interval_low, 2),
        "interval_high": round(interval_high, 2),
        "model_rmse": round(rmse, 2) if rmse is not None else None,
        "model_mae": round(metrics.get("mae"), 2) if metrics.get("mae") is not None else None,
        "model_r2": round(metrics.get("r2"), 4) if metrics.get("r2") is not None else None,
        "ensemble_size": 1,
    }


def load_model(ticker: str) -> tuple[Any, dict[str, Any]]:
    """Load a trained XGBoost booster + metadata from the registry."""
    path = model_file(ticker)
    if not path.exists():
        raise FileNotFoundError(
            f"No model for '{ticker}' at {path}. Run `python train.py --ticker {ticker}` first."
        )
    booster = xgb.Booster()
    booster.load_model(str(path))
    meta: dict[str, Any] = {"ticker": ticker, "features": FEATURE_COLUMNS}
    if meta_file(ticker).exists():
        meta = json.loads(meta_file(ticker).read_text())
    return booster, meta
