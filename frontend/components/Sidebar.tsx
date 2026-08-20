"use client";

import MarketMonitor from "@/components/MarketMonitor";
import type { ConnectionStatus } from "@/hooks/useWebSocket";

export type View =
  | "dashboard"
  | "pools"
  | "predictions"
  | "price"
  | "alerts"
  | "bot"
  | "settings";

const NAV_ITEMS: { key: View; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "pools", label: "Pools" },
  { key: "predictions", label: "Predictions" },
  { key: "price", label: "Price Prediction" },
  { key: "alerts", label: "Alerts" },
  { key: "bot", label: "Market Maker" },
  { key: "settings", label: "Settings" },
];

function statusStyles(status: ConnectionStatus): { label: string } {
  switch (status) {
    case "open":
      return { label: "LIVE" };
    case "connecting":
      return { label: "LINKING" };
    case "error":
      return { label: "ERROR" };
    default:
      return { label: "OFFLINE" };
  }
}

interface SidebarProps {
  status: ConnectionStatus;
  active: View;
  onNavigate: (view: View) => void;
  monitorActive: string;
  onPredictTicker: (ticker: string) => void;
}

export default function Sidebar({
  status,
  active,
  onNavigate,
  monitorActive,
  onPredictTicker,
}: SidebarProps) {
  const live = status === "open";
  const statusInfo = statusStyles(status);

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-noir-line bg-black">
      <div className="border-b border-noir-line p-3">
        <h1 className="text-sm font-bold uppercase leading-tight tracking-[0.18em] text-noir-amber text-glow">
          DEX Liquidity
          <br />
          Predictor
        </h1>
        <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-noir-dim">
          Uniswap V3 Terminal
        </p>
      </div>

      <nav className="flex-1 space-y-px p-2">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => onNavigate(item.key)}
            className={`block w-full border-l-2 px-3 py-1.5 text-left text-xs uppercase tracking-[0.14em] transition-colors ${
              item.key === active
                ? "border-noir-amber bg-noir-panel2 font-bold text-noir-amber"
                : "border-transparent text-noir-muted hover:bg-noir-panel2 hover:text-noir-text"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <MarketMonitor active={monitorActive} onPredict={onPredictTicker} />

      <div className="flex items-center gap-2 border-t border-noir-line px-3 py-2.5 text-[10px] uppercase tracking-[0.16em] text-noir-dim">
        <span
          className={`h-2 w-2 rounded-full ${
            live ? "bg-noir-orange dot-glow animate-pulse" : "bg-noir-line"
          }`}
          aria-hidden="true"
        />
        <span>WS: {statusInfo.label}</span>
      </div>
    </aside>
  );
}
