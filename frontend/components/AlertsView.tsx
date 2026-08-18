"use client";

import EmptyPanel from "@/components/EmptyPanel";
import RiskBadge from "@/components/RiskBadge";
import { formatPct } from "@/lib/format";
import type { AlertMessage, EventMessage } from "@/lib/types";

interface AlertsViewProps {
  alerts: AlertMessage[];
  events: EventMessage[];
}

export default function AlertsView({ alerts, events }: AlertsViewProps) {
  const highRiskEvents = events.filter(
    (event) => event.prediction?.risk_level === "High",
  );

  if (alerts.length === 0 && highRiskEvents.length === 0) {
    return (
      <EmptyPanel
        title="Alerts"
        text="No alerts yet — high-risk liquidity events will appear here."
      />
    );
  }

  return (
    <div className="space-y-4">
      {[...alerts].reverse().map((alert, index) => (
        <div
          key={`alert-${alert.timestamp}-${index}`}
          className="rounded-xl border border-red-500/30 bg-red-500/5 p-4"
        >
          <div className="mb-2 flex items-center justify-between gap-3">
            <RiskBadge level={alert.level} />
            <span className="text-xs text-slate-500">
              {new Date(alert.timestamp * 1000).toLocaleString()}
            </span>
          </div>
          <p className="text-sm text-slate-200">{alert.message}</p>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400">
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
      ))}

      {[...highRiskEvents].reverse().map((event, index) => (
        <div
          key={`event-${event.transaction_hash ?? ""}-${index}`}
          className="rounded-xl border border-red-500/30 bg-red-500/5 p-4"
        >
          <div className="mb-2 flex items-center justify-between gap-3">
            <RiskBadge level={event.prediction?.risk_level ?? "High"} />
            <span className="text-xs text-slate-500">
              {new Date(event.timestamp * 1000).toLocaleString()}
            </span>
          </div>
          <p className="text-sm text-slate-200">
            Warning: {event.pair} pool is predicted to experience a{" "}
            {formatPct(event.prediction?.predicted_drain_percentage)} liquidity
            drain in the next 3 blocks with an estimated price impact of{" "}
            {formatPct(event.prediction?.predicted_price_impact)}.
          </p>
        </div>
      ))}
    </div>
  );
}
