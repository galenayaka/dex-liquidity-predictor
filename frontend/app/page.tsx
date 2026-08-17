"use client";

import { useMemo } from "react";
import AlertBanner from "@/components/AlertBanner";
import LiquidityChart from "@/components/LiquidityChart";
import PredictionPanel from "@/components/PredictionPanel";
import PricePanel from "@/components/PricePanel";
import Sidebar from "@/components/Sidebar";
import { useWebSocket } from "@/hooks/useWebSocket";
import type {
  AlertMessage,
  EventMessage,
  LiquidityPoint,
  PoolState,
} from "@/lib/types";

export default function Dashboard() {
  const { status, lastMessage, messages } = useWebSocket();

  const pools = useMemo<PoolState[]>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.type === "snapshot") return message.data;
    }
    return [];
  }, [messages]);

  const latestEvent = useMemo<EventMessage | null>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.type === "event") return message;
    }
    return null;
  }, [messages]);

  const latestAlert = useMemo<AlertMessage | null>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.type === "alert") return message;
    }
    return null;
  }, [messages]);

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

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100">
      <Sidebar status={status} />

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl space-y-6 p-6">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">Liquidity Dashboard</h2>
              <p className="text-sm text-slate-400">
                Real-time Uniswap v3 pool prices &amp; liquidity-drain
                predictions
              </p>
            </div>
            <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-300">
              Last update:{" "}
              {lastUpdate != null
                ? new Date(lastUpdate * 1000).toLocaleTimeString()
                : "—"}
            </span>
          </header>

          <AlertBanner event={latestEvent} alert={latestAlert} />

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <PricePanel pools={pools} />
            </div>
            <PredictionPanel event={latestEvent} alert={latestAlert} />
          </div>

          <LiquidityChart data={liquiditySeries} />
        </div>
      </main>
    </div>
  );
}
