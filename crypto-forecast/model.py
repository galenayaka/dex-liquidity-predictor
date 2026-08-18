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


def save_model(
    model: Any,
    features: list[str],
    target_type: str,
    ticker: str,
    metrics: dict[str, Any] | None = None,
) -> None:
    """Persist the fitted model + metadata needed by the serving API."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / f"{ticker}_{target_type}_model.joblib")
    meta = {
        "features": features,
        "target_type": target_type,
        "ticker": ticker,
        "metrics": metrics or {},
    }
    (MODEL_DIR / f"{ticker}_{target_type}_meta.json").write_text(
        json.dumps(meta, indent=2)
    )
    logger.info("Saved model to %s", MODEL_DIR)


def _member_predictions(model: Any, row: pd.DataFrame) -> list[float]:
    """Collect each base estimator's prediction (works for sklearn ensembles)."""
    if hasattr(model, "estimators_"):
        preds: list[float] = []
        for item in model.estimators_:
            est = item[1] if isinstance(item, tuple) else item
            preds.append(float(est.predict(row)[0]))
        return preds
    return [float(model.predict(row)[0])]


def predict_with_uncertainty(
    model: Any, row: pd.DataFrame, meta: dict[str, Any]
) -> dict[str, Any]:
    """Return the forecast plus confidence / interval / model-quality info.

    Regression: confidence reflects how closely the ensemble members agree,
    scaled by the held-out test RMSE; the interval is ŷ ± 1.96·RMSE.
    Classification: confidence is the predicted class probability.
    """
    target_type = meta["target_type"]
    metrics: dict[str, Any] = meta.get("metrics", {})

    if target_type == "classification":
        direction = int(model.predict(row)[0])
        proba = float(model.predict_proba(row)[0][1])
        conf = proba if direction == 1 else 1.0 - proba
        acc = metrics.get("accuracy")
        return {
            "ticker": meta.get("ticker"),
            "target_type": target_type,
            "predicted_direction": direction,
            "probability_up": proba,
            "confidence": round(conf * 100.0, 1),
            "model_accuracy": round(acc, 4) if acc is not None else None,
        }

    price = float(model.predict(row)[0])
    member_preds = _member_predictions(model, row)
    spread = (
        float(max(member_preds) - min(member_preds))
        if len(member_preds) > 1
        else 0.0
    )

    rmse = metrics.get("rmse")
    if rmse and rmse > 0:
        interval_low = price - 1.96 * rmse
        interval_high = price + 1.96 * rmse
        # Perfect agreement -> 100; disagreement of 2·RMSE -> 0.
        confidence = max(0.0, 100.0 * (1.0 - spread / (2.0 * rmse)))
    else:
        interval_low = interval_high = None
        confidence = None

    return {
        "ticker": meta.get("ticker"),
        "target_type": target_type,
        "predicted_price": price,
        "confidence": round(confidence, 1) if confidence is not None else None,
        "interval_low": round(interval_low, 2) if interval_low is not None else None,
        "interval_high": round(interval_high, 2) if interval_high is not None else None,
        "model_rmse": round(rmse, 2) if rmse is not None else None,
        "model_mae": round(metrics.get("mae"), 2) if metrics.get("mae") is not None else None,
        "model_r2": round(metrics.get("r2"), 4) if metrics.get("r2") is not None else None,
        "ensemble_size": len(member_preds),
    }


def load_model(ticker: str, target_type: str = TARGET_TYPE) -> tuple[Any, dict[str, Any]]:
    """Load a trained model and its metadata."""
    model_path = MODEL_DIR / f"{ticker}_{target_type}_model.joblib"
    meta_path = MODEL_DIR / f"{ticker}_{target_type}_meta.json"
    if not model_path.exists():
        raise FileNotFoundError(
            f"No trained model at {model_path}. Run `python train.py --ticker {ticker}` first."
        )
    return joblib.load(model_path), json.loads(meta_path.read_text())
