"""Train the XGBoost liquidity-drain classifier on synthetic data.

Usage (from the `backend` directory):
    python -m scripts.train_model
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.ml.features import FEATURE_NAMES  # noqa: E402
from app.ml.model import XGBDrainModel  # noqa: E402


def generate_dataset(n: int = 20_000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = np.zeros((n, len(FEATURE_NAMES)), dtype=float)
    y = np.zeros(n, dtype=int)

    for i in range(n):
        liq_1m = rng.normal(0.0, 0.08)
        liq_5m = rng.normal(0.0, 0.12)
        liq_15m = rng.normal(0.0, 0.15)
        impact = rng.gamma(2.0, 1.0)          # reference trade impact magnitude (%)
        pending = rng.poisson(3.0)
        fee = rng.choice([100, 500, 3000, 10000])
        log_liq = rng.normal(11.0, 1.0)
        vol = rng.gamma(1.5, 0.01)

        # Synthetic "drain risk" logit — drains are driven by negative liquidity
        # changes, large reference impact and elevated volatility.
        risk = (
            -liq_1m * 3.0
            - liq_5m * 2.0
            - liq_15m * 1.0
            + impact * 0.05
            + pending * 0.02
            + vol * 5.0
        )
        probability = 1.0 / (1.0 + np.exp(-(risk - 0.2)))
        label = int(rng.random() < probability)

        X[i] = [liq_1m, liq_5m, liq_15m, impact, pending, fee, log_liq, vol]
        y[i] = label

    return X, y


def main() -> None:
    settings = get_settings()
    print(f"Generating synthetic training data for features: {FEATURE_NAMES}")
    X, y = generate_dataset()
    positive_rate = float(np.mean(y))
    print(f"Samples: {len(y)} | positive (drain) rate: {positive_rate:.3f}")

    model = XGBDrainModel(settings.model_path)
    model.fit(X, y)
    model.save()
    print(f"Model written to {settings.model_path}")


if __name__ == "__main__":
    main()
