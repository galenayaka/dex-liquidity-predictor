"use client";

import { useState } from "react";
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
}

export default function PricePredictionView() {
  const [ticker, setTicker] = useState<Ticker>("btc");
  const [values, setValues] = useState<Record<FieldKey, number>>(
    TICKER_DEFAULTS.btc,
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectTicker = (key: Ticker) => {
    setTicker(key);
    setValues(TICKER_DEFAULTS[key]);
    setResult(null);
    setError(null);
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
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
