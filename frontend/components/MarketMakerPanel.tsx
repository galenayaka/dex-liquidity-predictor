"use client";

import { useEffect, useState } from "react";
import type { MarketMakerState } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-noir-line px-3 py-1.5 last:border-0">
      <span className="text-[10px] uppercase tracking-[0.14em] text-noir-dim">
        {label}
      </span>
      <span className="text-xs font-semibold text-noir-text">{children}</span>
    </div>
  );
}

/**
 * MarketMakerPanel — shows the execution-layer bot's current position.
 *
 * The state normally arrives over the WebSocket (`live` prop, message type
 * `bot`); on mount the panel also fetches the REST status endpoint as an
 * initial/fallback source and polls it every 5 s while the WS is quiet.
 */
export default function MarketMakerPanel({
  live,
}: {
  live?: MarketMakerState | null;
}) {
  const [rest, setRest] = useState<MarketMakerState | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${API_URL}/api/v1/market-maker/status`, {
          signal: controller.signal,
        });
        if (!res.ok) return;
        const data = (await res.json()) as MarketMakerState;
        if (!cancelled) setRest(data);
      } catch {
        // Backend offline — keep the last known state.
      } finally {
        clearTimeout(timer);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const state = live ?? rest;
  const active = state?.has_active_position ?? false;

  return (
    <section className="panel">
      <div className="panel-head flex items-center justify-between">
        <div>
          <h3 className="panel-title">Market Maker Bot</h3>
          <p className="panel-sub">Simulated Uniswap v3 execution layer</p>
        </div>
        <span
          className={`border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
            active
              ? "border-noir-green bg-noir-green/10 text-noir-green"
              : "border-noir-line bg-noir-panel text-noir-dim"
          }`}
        >
          {active ? "Position Open" : "Idle"}
        </span>
      </div>

      {state ? (
        <div>
          <Row label="Simulation mode">
            {state.simulation_mode ? "SIMULATED" : "LIVE"}
          </Row>
          <Row label="Tick range">
            [{state.tick_lower.toLocaleString()}, {state.tick_upper.toLocaleString()}]
          </Row>
          <Row label="Range width">
            {((state.tick_upper - state.tick_lower) / Math.max(1, state.tick_spacing)).toFixed(0)}× spacing
          </Row>
          <Row label="Tick spacing">{state.tick_spacing}</Row>
          <Row label="Liquidity">{state.liquidity.toLocaleString()}</Row>
          <Row label="Token ID">{state.token_id ?? "—"}</Row>
        </div>
      ) : (
        <p className="border-t border-noir-line px-3 py-2 text-[10px] uppercase tracking-wider text-noir-dim">
          Awaiting bot state…
        </p>
      )}

      <p className="border-t border-noir-line px-3 py-2 text-[10px] uppercase tracking-wider text-noir-dim">
        Policy: withdraw on HIGH/CRITICAL · provide on LOW · hold otherwise
      </p>
    </section>
  );
}
