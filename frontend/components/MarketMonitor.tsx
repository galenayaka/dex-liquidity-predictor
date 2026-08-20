/**
 * MarketMonitor — compact ticker table for the sidebar.
 *
 * Polls the forecast service's GET /snapshot every 30 seconds (with an 8 s
 * abort timeout) and shows each coin's price and 24 h change, plus a one-click
 * "predict" action that forwards the ticker to the dashboard.
 */
"use client";

import { useEffect, useState } from "react";

const FORECAST_URL =
  process.env.NEXT_PUBLIC_FORECAST_URL ?? "http://localhost:8100";

const TICKERS = ["btc", "eth", "sol", "bnb", "xrp"] as const;

interface CoinQuote {
  price?: number | null;
  change_24h?: number | null;
}

interface Snapshot {
  as_of?: string | null;
  [ticker: string]: unknown;
}

interface MarketMonitorProps {
  active: string;
  onPredict: (ticker: string) => void;
}

export default function MarketMonitor({ active, onPredict }: MarketMonitorProps) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 8000);
        const res = await fetch(`${FORECAST_URL}/snapshot`, {
          signal: controller.signal,
        });
        clearTimeout(timer);
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as Snapshot;
        if (!cancelled) setSnapshot(data);
      } catch {
        // keep previous snapshot
      }
    };
    void load();
    const id = setInterval(() => void load(), 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="border-t border-noir-line p-2">
      <div className="mb-1 flex items-center justify-between px-1">
        <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-noir-dim">
          Market Monitor
        </span>
        {snapshot?.as_of ? (
          <span className="text-[9px] text-noir-dim">
            {snapshot.as_of.slice(5)}
          </span>
        ) : null}
      </div>

      <table className="w-full border-collapse font-mono text-[10px]">
        <thead>
          <tr className="text-noir-dim">
            <th className="pb-1 text-left font-normal">TICK</th>
            <th className="pb-1 text-right font-normal">PRICE</th>
            <th className="pb-1 text-right font-normal">24H</th>
            <th className="pb-1 text-right font-normal">ACT</th>
          </tr>
        </thead>
        <tbody>
          {TICKERS.map((t) => {
            const quote = snapshot?.[t] as CoinQuote | undefined;
            const price = quote?.price ?? null;
            const change = quote?.change_24h ?? null;
            const isActive = t === active;
            return (
              <tr
                key={t}
                className={
                  isActive ? "text-noir-amber" : "text-noir-text"
                }
              >
                <td className="py-0.5 pr-1 text-left font-bold uppercase">
                  {t}
                </td>
                <td className="py-0.5 text-right tabular-nums">
                  {price != null
                    ? price.toLocaleString(undefined, {
                        maximumFractionDigits: t === "xrp" ? 4 : 2,
                      })
                    : "—"}
                </td>
                <td
                  className={`py-0.5 text-right tabular-nums ${
                    change == null
                      ? "text-noir-dim"
                      : change >= 0
                        ? "text-noir-amber"
                        : "text-noir-blood"
                  }`}
                >
                  {change == null
                    ? "—"
                    : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`}
                </td>
                <td className="py-0.5 text-right">
                  <button
                    type="button"
                    onClick={() => onPredict(t)}
                    className="border border-noir-line px-1 text-[9px] font-bold leading-4 text-noir-muted hover:border-noir-amber hover:text-noir-amber"
                    title={`Predict ${t.toUpperCase()}`}
                  >
                    →
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
