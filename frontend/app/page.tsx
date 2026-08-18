"use client";

import { useMemo, useState } from "react";
import AlertBanner from "@/components/AlertBanner";
import AlertsView from "@/components/AlertsView";
import Explain from "@/components/Explain";
import LiquidityChart from "@/components/LiquidityChart";
import PoolsView from "@/components/PoolsView";
import PredictionPanel from "@/components/PredictionPanel";
import PredictionsView from "@/components/PredictionsView";
import PricePanel from "@/components/PricePanel";
import SettingsView from "@/components/SettingsView";
import Sidebar, { type View } from "@/components/Sidebar";
import { useWebSocket } from "@/hooks/useWebSocket";
import type {
  AlertMessage,
  EventMessage,
  LiquidityPoint,
  PoolState,
} from "@/lib/types";

const VIEW_TITLES: Record<View, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Liquidity Dashboard",
    subtitle: "Real-time Uniswap v3 pool prices & liquidity-drain predictions",
  },
  pools: {
    title: "Pools",
    subtitle: "Watched Uniswap v3 pools and historical liquidity",
  },
  predictions: {
    title: "Predictions",
    subtitle: "Live AI predictions for recent on-chain events",
  },
  alerts: {
    title: "Alerts",
    subtitle: "High-risk liquidity alerts and warnings",
  },
  settings: {
    title: "Settings",
    subtitle: "Connection and application configuration",
  },
};

export default function Dashboard() {
  const [view, setView] = useState<View>("dashboard");
  const { status, lastMessage, messages } = useWebSocket();

  const pools = useMemo<PoolState[]>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.type === "snapshot") return message.data;
    }
    return [];
  }, [messages]);

  const events = useMemo<EventMessage[]>(
    () => messages.filter((m): m is EventMessage => m.type === "event"),
    [messages],
  );

  const alerts = useMemo<AlertMessage[]>(
    () => messages.filter((m): m is AlertMessage => m.type === "alert"),
    [messages],
  );

  const latestEvent = useMemo<EventMessage | null>(
    () => events[events.length - 1] ?? null,
    [events],
  );

  const latestAlert = useMemo<AlertMessage | null>(
    () => alerts[alerts.length - 1] ?? null,
    [alerts],
  );

  const lastUpdate = useMemo(() => {
    if (!lastMessage || lastMessage.type === "snapshot") return null;
    return lastMessage.timestamp;
  }, [lastMessage]);

  const liquiditySeries = useMemo<LiquidityPoint[]>(() => {
    const points: LiquidityPoint[] = [];
    let lastTime = 0;
    for (const message of messages) {
      if (message.type !== "event") continue;
      const raw = message.args?.liquidity;
      const value =
        typeof raw === "string"
          ? Number(raw)
          : typeof raw === "number"
            ? raw
            : Number.NaN;
      if (!Number.isFinite(value) || value <= 0) continue;
      let time = message.timestamp;
      if (time <= lastTime) time = lastTime + 1;
      lastTime = time;
      points.push({ time, value: value / 1e18 });
    }
    return points;
  }, [messages]);

  const heading = VIEW_TITLES[view];

  return (
    <div className="flex h-screen w-full bg-black text-noir-text">
      <Sidebar status={status} active={view} onNavigate={setView} />

      <main className="flex-1 overflow-y-auto">
        <div className="space-y-3 p-3">
          <header className="flex flex-wrap items-end justify-between gap-2 border-b border-noir-line pb-2">
            <div>
              <h2 className="text-lg font-bold uppercase tracking-[0.18em] text-noir-amber text-glow">
                {heading.title}
              </h2>
              <p className="text-[10px] uppercase tracking-[0.16em] text-noir-dim">
                {heading.subtitle}
              </p>
            </div>
            <span className="border border-noir-line bg-noir-panel px-2 py-0.5 text-[10px] uppercase tracking-wider text-noir-muted">
              Last update{" "}
              {lastUpdate != null
                ? new Date(lastUpdate * 1000).toLocaleTimeString()
                : "—"}
            </span>
          </header>

          <AlertBanner event={latestEvent} alert={latestAlert} />

          {view === "dashboard" && (
            <>
              <Explain title="How to read this dashboard" open>
                <p>
                  This terminal watches Uniswap v3 liquidity pools on Ethereum in
                  real time. An AI model reads every trade and withdrawal, then
                  predicts when a pool might lose liquidity — a{" "}
                  <b>liquidity drain</b> — and how that would move prices. It is
                  an early-warning system for traders and liquidity providers.
                </p>
                <p className="mt-1">
                  <b>Liquidity pool</b> — a pot of two tokens (e.g. USDC/WETH)
                  that traders swap against.
                  <br />
                  <b>Liquidity drain</b> — providers withdrawing tokens, thinning
                  the pool.
                  <br />
                  <b>Price impact</b> — how much a trade moves the price (high =
                  slippage).
                  <br />
                  <b>TVL</b> — total dollar value locked in a pool (bigger =
                  healthier).
                  <br />
                  <b>Risk level</b> — how likely the AI thinks a drain is (Low /
                  Medium / High).
                </p>
              </Explain>

              <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
                <div className="xl:col-span-2">
                  <PricePanel pools={pools} />
                </div>
                <PredictionPanel event={latestEvent} alert={latestAlert} />
              </div>

              <LiquidityChart data={liquiditySeries} />

              <Explain title="Why liquidity movements matter">
                When providers withdraw from a pool, every trade moves the price
                more — trading gets more expensive and the token can swing
                sharply. A falling liquidity line (or a Burn event) is the early
                warning sign.
              </Explain>
            </>
          )}

          {view === "pools" && <PoolsView pools={pools} />}
          {view === "predictions" && <PredictionsView events={events} />}
          {view === "alerts" && <AlertsView alerts={alerts} events={events} />}
          {view === "settings" && <SettingsView status={status} />}
        </div>
      </main>
    </div>
  );
}
