"""XGBoost classifier wrapper (train / save / load / predict)."""
from __future__ import annotations

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)


class XGBDrainModel:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._model = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            logger.info("No model at %s — heuristic fallback will be used", self.model_path)
            return False
        try:
            import xgboost as xgb

            self._model = xgb.XGBClassifier()
            self._model.load_model(self.model_path)
            logger.info("Loaded XGBoost model from %s", self.model_path)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load model: %s", exc)
            return False

    def fit(self, X, y) -> None:
        import xgboost as xgb

        self._model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42,
        )
        self._model.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=int))

    def predict_proba(self, X) -> list[float]:
        """Return the positive-class (drain) probability for each row."""
        if not self.loaded:
            return [0.0] * len(X)
        probs = self._model.predict_proba(np.asarray(X, dtype=float))
        return [float(p[1]) for p in probs]

    def save(self) -> None:
        if not self.loaded:
            raise RuntimeError("Cannot save: no fitted model")
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        self._model.save_model(self.model_path)
        logger.info("Saved model to %s", self.model_path)
