"use client";

import type { ReactNode } from "react";
import { formatPct, shortenAddress } from "@/lib/format";
import type { AlertMessage, EventMessage } from "@/lib/types";

interface PredictionPanelProps {
  event: EventMessage | null;
  alert: AlertMessage | null;
}

const BADGE_COLORS: Record<string, string> = {
  Low: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  Medium: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  High: "bg-red-500/15 text-red-300 border-red-500/30",
  LOW: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  HIGH: "bg-red-500/15 text-red-300 border-red-500/30",
  CRITICAL: "bg-rose-600/20 text-rose-200 border-rose-500/40",
};

function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        BADGE_COLORS[level] ?? "bg-slate-700 text-slate-200 border-slate-600"
      }`}
    >
      {level}
    </span>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-slate-400">{label}</span>
      {children}
    </div>
  );
}

export default function PredictionPanel({
  event,
  alert,
}: PredictionPanelProps) {
  const prediction = event?.prediction;

  return (
    <section className="space-y-6 rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div>
        <h3 className="font-semibold text-slate-100">Liquidity Prediction</h3>
        <p className="text-xs text-slate-400">
          Latest on-chain event inference
        </p>
      </div>

      {prediction ? (
        <div className="space-y-3">
          <Row label="Event">
            <span className="text-sm font-medium text-slate-100">
              {event?.event} · {event?.pair}
            </span>
          </Row>
          <Row label="Risk level">
            <RiskBadge level={prediction.risk_level} />
          </Row>
          <Row label="Drain prediction">
            <span className="text-sm font-semibold text-red-300">
              {formatPct(prediction.predicted_drain_percentage)}
            </span>
          </Row>
          <Row label="Price impact">
            <span className="text-sm font-semibold text-slate-100">
              {formatPct(prediction.predicted_price_impact)}
            </span>
          </Row>
          {event?.transaction_hash && (
            <Row label="Transaction">
              <span className="font-mono text-xs text-slate-500">
                {shortenAddress(event.transaction_hash)}
              </span>
            </Row>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          No prediction yet — waiting for Swap/Burn events…
        </p>
      )}

      {alert && (
        <div className="space-y-2 border-t border-slate-800 pt-4">
          <RiskBadge level={alert.level} />
          <p className="text-sm text-slate-300">{alert.message}</p>
          <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
            <div>
              Drain probability:{" "}
              <span className="text-slate-200">
                {alert.drain_probability != null
                  ? `${(alert.drain_probability * 100).toFixed(1)}%`
                  : "—"}
              </span>
            </div>
            <div>
              Impact:{" "}
              <span className="text-slate-200">
                {formatPct(alert.price_impact_pct)}
              </span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
