"use client";

import type { ConnectionStatus } from "@/hooks/useWebSocket";

export type View =
  | "dashboard"
  | "pools"
  | "predictions"
  | "alerts"
  | "settings";

const NAV_ITEMS: { key: View; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "pools", label: "Pools" },
  { key: "predictions", label: "Predictions" },
  { key: "alerts", label: "Alerts" },
  { key: "settings", label: "Settings" },
];

function statusStyles(status: ConnectionStatus): { dot: string; label: string } {
  switch (status) {
    case "open":
      return { dot: "bg-emerald-400", label: "Live" };
    case "connecting":
      return { dot: "bg-amber-400", label: "Connecting" };
    case "error":
      return { dot: "bg-rose-400", label: "Error" };
    default:
      return { dot: "bg-slate-500", label: "Offline" };
  }
}

interface SidebarProps {
  status: ConnectionStatus;
  active: View;
  onNavigate: (view: View) => void;
}

export default function Sidebar({ status, active, onNavigate }: SidebarProps) {
  const statusInfo = statusStyles(status);

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 p-5">
        <h1 className="text-base font-semibold text-slate-100">
          DEX Liquidity Predictor
        </h1>
        <p className="mt-1 text-xs text-slate-400">Uniswap v3 analytics</p>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => onNavigate(item.key)}
            className={`block w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
              item.key === active
                ? "bg-slate-800 font-medium text-white"
                : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-2 border-t border-slate-800 p-4 text-xs text-slate-400">
        <span
          className={`h-2 w-2 rounded-full ${statusInfo.dot}`}
          aria-hidden="true"
        />
        <span>WebSocket: {statusInfo.label}</span>
      </div>
    </aside>
  );
}
