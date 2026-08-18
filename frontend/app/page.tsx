"use client";

import { useMemo, useState } from "react";
import AlertBanner from "@/components/AlertBanner";
import AlertsView from "@/components/AlertsView";
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
    <div className="flex h-screen w-full bg-slate-950 text-slate-100">
      <Sidebar status={status} active={view} onNavigate={setView} />

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl space-y-6 p-6">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">{heading.title}</h2>
              <p className="text-sm text-slate-400">{heading.subtitle}</p>
            </div>
            <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-300">
              Last update:{" "}
              {lastUpdate != null
                ? new Date(lastUpdate * 1000).toLocaleTimeString()
                : "—"}
            </span>
          </header>

          <AlertBanner event={latestEvent} alert={latestAlert} />

          {view === "dashboard" && (
            <>
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <div className="xl:col-span-2">
                  <PricePanel pools={pools} />
                </div>
                <PredictionPanel event={latestEvent} alert={latestAlert} />
              </div>

              <LiquidityChart data={liquiditySeries} />
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
