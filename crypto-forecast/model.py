"""Model training, evaluation and persistence (XGBoost ensemble)."""
from __future__ import annotations

import json
import logging
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, VotingClassifier, VotingRegressor
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from config import MODEL_DIR, SEED, TARGET_TYPE, TRAIN_SPLIT

logger = logging.getLogger(__name__)


def chronological_split(df: pd.DataFrame, split: float = TRAIN_SPLIT) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Time-ordered split (no shuffle) to prevent look-ahead bias."""
    cut = int(len(df) * split)
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


def build_model(target_type: str = TARGET_TYPE, ensemble: bool = True):
    """Build a scaled pipeline: XGBoost alone, or an XGBoost + HistGBM ensemble."""
    if target_type == "classification":
        xgb = XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9, random_state=SEED,
        )
        hgb = HistGradientBoostingClassifier(random_state=SEED)
    else:
        xgb = XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9, random_state=SEED,
        )
        hgb = HistGradientBoostingRegressor(random_state=SEED)

    xgb_pipe = Pipeline([("scaler", StandardScaler()), ("xgb", xgb)])
    hgb_pipe = Pipeline([("scaler", StandardScaler()), ("hgb", hgb)])

    if ensemble:
        if target_type == "classification":
            return VotingClassifier([("xgb", xgb_pipe), ("hgb", hgb_pipe)], voting="soft")
        return VotingRegressor([("xgb", xgb_pipe), ("hgb", hgb_pipe)])

    return xgb_pipe


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, target_type: str) -> dict[str, Any]:
    """Compute regression or classification metrics."""
    if target_type == "classification":
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "classification_report": classification_report(
                y_true, y_pred, output_dict=True, zero_division=0
            ),
        }
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def train(
    df: pd.DataFrame,
    features: list[str],
    target_type: str = TARGET_TYPE,
    ensemble: bool = True,
) -> tuple[Any, dict[str, Any], pd.DataFrame]:
    """Train on the chronological train split and evaluate on the test split."""
    train_df, test_df = chronological_split(df)
    X_train, y_train = train_df[features], train_df["target"]
    X_test, y_test = test_df[features], test_df["target"]

    model = build_model(target_type, ensemble=ensemble)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = evaluate(y_test.to_numpy(), y_pred, target_type)

    results = test_df[["close", "target"]].copy()
    results["prediction"] = y_pred
    return model, metrics, results


def save_model(model: Any, features: list[str], target_type: str, ticker: str) -> None:
    """Persist the fitted model + metadata needed by the serving API."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / f"{ticker}_{target_type}_model.joblib")
    meta = {"features": features, "target_type": target_type, "ticker": ticker}
    (MODEL_DIR / f"{ticker}_{target_type}_meta.json").write_text(
        json.dumps(meta, indent=2)
    )
    logger.info("Saved model to %s", MODEL_DIR)


def load_model(ticker: str, target_type: str = TARGET_TYPE) -> tuple[Any, dict[str, Any]]:
    """Load a trained model and its metadata."""
    model_path = MODEL_DIR / f"{ticker}_{target_type}_model.joblib"
    meta_path = MODEL_DIR / f"{ticker}_{target_type}_meta.json"
    if not model_path.exists():
        raise FileNotFoundError(
            f"No trained model at {model_path}. Run `python train.py --ticker {ticker}` first."
        )
    return joblib.load(model_path), json.loads(meta_path.read_text())
