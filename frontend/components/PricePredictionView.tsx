"use client";

import { useEffect, useState } from "react";
import Explain from "@/components/Explain";

const FORECAST_URL =
  process.env.NEXT_PUBLIC_FORECAST_URL ?? "http://localhost:8100";

type Ticker = "btc" | "eth";

type FieldKey =
  | "open"
  | "high"
  | "low"
  | "close"
  | "volume"
  | "sp500_close"
  | "dxy"
  | "gold"
  | "treasury_10y"
  | "gpr";

const FIELDS: { key: FieldKey; label: string }[] = [
  { key: "open", label: "Open" },
  { key: "high", label: "High" },
  { key: "low", label: "Low" },
  { key: "close", label: "Close" },
  { key: "volume", label: "Volume" },
  { key: "sp500_close", label: "S&P 500" },
  { key: "dxy", label: "DXY" },
  { key: "gold", label: "Gold (USD/oz)" },
  { key: "treasury_10y", label: "10Y Yield (%)" },
  { key: "gpr", label: "GPR Index" },
];

const TICKER_DEFAULTS: Record<Ticker, Record<FieldKey, number>> = {
  btc: {
    open: 65000, high: 66200, low: 64800, close: 65900, volume: 3.2e10,
    sp500_close: 5300, dxy: 104.2, gold: 2350, treasury_10y: 4.25, gpr: 95,
  },
  eth: {
    open: 3450, high: 3520, low: 3400, close: 3480, volume: 1.8e10,
    sp500_close: 5300, dxy: 104.2, gold: 2350, treasury_10y: 4.25, gpr: 95,
  },
};

interface ForecastResult {
  ticker: string;
  target_type: string;
  predicted_price?: number | null;
  predicted_direction?: number | null;
  probability_up?: number | null;
  confidence?: number | null;
  interval_low?: number | null;
  interval_high?: number | null;
  model_rmse?: number | null;
  model_mae?: number | null;
  model_r2?: number | null;
  model_accuracy?: number | null;
  ensemble_size?: number | null;
}

export default function PricePredictionView() {
  const [ticker, setTicker] = useState<Ticker>("btc");
  const [values, setValues] = useState<Record<FieldKey, number>>(
    TICKER_DEFAULTS.btc,
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [fetchingLatest, setFetchingLatest] = useState(false);

  const loadLatest = async (key: Ticker) => {
    setFetchingLatest(true);
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${FORECAST_URL}/latest/${key}`, {
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) return;
      const data: unknown = await res.json().catch(() => null);
      if (!data || typeof data !== "object") return;
      const feats = (data as { features?: unknown }).features;
      if (feats && typeof feats === "object") {
        const featMap = feats as Record<string, unknown>;
        setValues((prev) => {
          const next = { ...prev };
          for (const f of FIELDS) {
            const v = Number(featMap[f.key]);
            if (Number.isFinite(v)) next[f.key] = v;
          }
          return next;
        });
      }
      const asOfValue = (data as { as_of?: unknown }).as_of;
      if (typeof asOfValue === "string") setAsOf(asOfValue);
    } catch {
      // keep example defaults if the service is unreachable
    } finally {
      setFetchingLatest(false);
    }
  };

  useEffect(() => {
    void loadLatest("btc");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectTicker = (key: Ticker) => {
    setTicker(key);
    setValues(TICKER_DEFAULTS[key]);
    setResult(null);
    setError(null);
    setAsOf(null);
    void loadLatest(key);
  };

  const setField = (key: FieldKey, raw: string) => {
    const num = Number(raw);
    setValues((prev) => ({ ...prev, [key]: Number.isFinite(num) ? num : 0 }));
  };

  const predict = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);

    try {
      const res = await fetch(`${FORECAST_URL}/predict/${ticker}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
        signal: controller.signal,
      });
      const data: unknown = await res.json().catch(() => null);
      if (!res.ok) {
        const detail =
          data && typeof data === "object" && "detail" in data
            ? String((data as { detail: unknown }).detail)
            : `HTTP ${res.status}`;
        setError(detail);
        return;
      }
      setResult(data as ForecastResult);
    } catch {
      setError(
        "Forecast service unreachable. In crypto-forecast run: " +
          "python train.py --ticker " +
          ticker +
          ", then uvicorn main:app --port 8100.",
      );
    } finally {
      clearTimeout(timer);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <Explain title="About price prediction" open>
        This calls a machine-learning service that forecasts the next-day price
        of <b>BTC</b> or <b>ETH</b> from today's crypto prices plus the stock
        market (S&amp;P 500), the dollar (DXY), gold, bond yields and geopolitical
        risk. Fill in the values (or keep the example defaults) and press{" "}
        <b>Predict</b>. It is an estimate, not financial advice.
      </Explain>

      <Explain title="Math: how the number is computed">
        <p className="mb-2">
          The model learns a function <code>f</code> that maps today&apos;s 10
          inputs to tomorrow&apos;s closing price.
        </p>
        <ol className="list-decimal space-y-1.5 pl-5">
          <li>
            <b>Target.</b> Each training day predicts the <i>next</i> day&apos;s
            close: <code>y_t = close_(t+1)</code> — so the answer is never fed
            in as an input.
          </li>
          <li>
            <b>Standardization.</b> Features are centered and scaled before
            training: <code>z = (x − μ) / σ</code>.
          </li>
          <li>
            <b>Gradient boosting.</b> Two tree ensembles minimize squared error{" "}
            <code>Σ (close_(t+1) − ŷ_t)²</code>:
            <ul className="ml-4 list-disc">
              <li><b>XGBoost</b> — 300 boosted decision trees (depth 5).</li>
              <li><b>HistGradientBoosting</b> — histogram-based boosted trees.</li>
            </ul>
          </li>
          <li>
            <b>Ensemble.</b> The forecast averages the two models:{" "}
            <code>ŷ = (xgb(x) + hgb(x)) / 2</code>.
          </li>
          <li>
            <b>Train/test split.</b> Chronological 80/20: the model trains on the
            past and is scored only on strictly future days (no look-ahead bias).
          </li>
          <li>
            <b>Confidence.</b> How closely the two models agree, scaled by typical
            error: <code>confidence = max(0, 100 × (1 − spread / (2·RMSE)))</code>.
            Perfect agreement → 100%.
          </li>
          <li>
            <b>95% interval.</b> <code>ŷ ± 1.96 × RMSE</code>, where RMSE is the
            model&apos;s error on the held-out test set.
          </li>
        </ol>
        <p className="mt-2">
          These are statistical estimates from historical patterns — not a
          guarantee of future price movement.
        </p>
      </Explain>

      <section className="panel max-w-3xl">
        <div className="panel-head">
          <h3 className="panel-title">Price Prediction</h3>
          <div className="flex gap-1">
            {(["btc", "eth"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => selectTicker(t)}
                className={`px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] ${
                  ticker === t
                    ? "border border-noir-amber bg-noir-panel2 text-noir-amber"
                    : "border border-noir-line text-noir-muted hover:text-noir-text"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="p-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {FIELDS.map((field) => (
              <label key={field.key} className="block">
                <span className="text-[10px] uppercase tracking-wider text-noir-dim">
                  {field.label}
                </span>
                <input
                  type="number"
                  step="any"
                  value={values[field.key]}
                  onChange={(e) => setField(field.key, e.target.value)}
                  className="mt-0.5 w-full border border-noir-line bg-black px-2 py-1 text-xs text-noir-text focus:border-noir-amber focus:outline-none"
                />
              </label>
            ))}
          </div>

          <div className="mt-2 flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-wider text-noir-dim">
              {fetchingLatest
                ? "Loading live data…"
                : asOf
                  ? `Live data as of ${asOf}`
                  : "Example defaults (live data unavailable)"}
            </span>
            <button
              type="button"
              onClick={() => void loadLatest(ticker)}
              disabled={fetchingLatest}
              className="border border-noir-line px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-noir-muted hover:text-noir-text disabled:opacity-50"
            >
              Reload latest
            </button>
          </div>

          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              onClick={predict}
              disabled={loading}
              className="border border-noir-amber bg-noir-amber px-4 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-black transition-colors hover:bg-noir-orange disabled:opacity-50"
            >
              {loading ? "Predicting…" : "Predict"}
            </button>
            {loading && (
              <span className="text-[10px] uppercase tracking-wider text-noir-dim">
                Running model…
              </span>
            )}
          </div>

          {error && (
            <div className="mt-3 border border-noir-blood bg-noir-panel2 px-3 py-2 text-xs leading-relaxed text-noir-blood">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-3 border border-noir-amber bg-noir-panel2 px-3 py-2">
              {result.target_type === "classification" ? (
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-noir-dim">
                    Predicted direction ({ticker.toUpperCase()})
                  </div>
                  <div className="text-2xl font-bold text-noir-amber text-glow">
                    {result.predicted_direction === 1 ? "UP ▲" : "DOWN ▼"}
                  </div>
                  <div className="mt-0.5 text-xs text-noir-muted">
                    Probability up:{" "}
                    {(((result.probability_up ?? 0) * 100)).toFixed(1)}%
                  </div>
                  {typeof result.confidence === "number" && (
                    <div className="mt-0.5 text-xs text-noir-muted">
                      Confidence: {result.confidence.toFixed(1)}%
                    </div>
                  )}
                  {result.model_accuracy != null && (
                    <div className="mt-1 text-[10px] uppercase tracking-wider text-noir-dim">
                      Model accuracy: {(result.model_accuracy * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-noir-dim">
                    Predicted next-day price ({ticker.toUpperCase()})
                  </div>
                  <div className="text-2xl font-bold text-noir-amber text-glow">
                    $
                    {(result.predicted_price ?? 0).toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </div>

                  {typeof result.confidence === "number" && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-noir-dim">
                        <span>Confidence</span>
                        <span className="text-noir-text">
                          {result.confidence.toFixed(1)}%
                        </span>
                      </div>
                      <div className="mt-0.5 h-1.5 w-full border border-noir-line bg-black">
                        <div
                          className="h-full bg-noir-amber"
                          style={{ width: `${Math.min(100, result.confidence)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {result.interval_low != null && result.interval_high != null && (
                    <div className="mt-2 text-xs text-noir-muted">
                      95% range:{" "}
                      <span className="text-noir-text">
                        $
                        {(result.interval_low ?? 0).toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}{" "}
                        – $
                        {(result.interval_high ?? 0).toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                      </span>
                    </div>
                  )}

                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px] uppercase tracking-wider text-noir-dim">
                    {result.model_r2 != null && <span>R² {result.model_r2.toFixed(3)}</span>}
                    {result.model_rmse != null && (
                      <span>
                        RMSE $
                        {(result.model_rmse ?? 0).toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                      </span>
                    )}
                    {result.model_mae != null && (
                      <span>
                        MAE $
                        {(result.model_mae ?? 0).toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                      </span>
                    )}
                    {result.ensemble_size != null && (
                      <span>{result.ensemble_size}-model ensemble</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
