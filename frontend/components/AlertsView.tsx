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

  const total = alerts.length + highRiskEvents.length;

  if (total === 0) {
    return (
      <EmptyPanel
        title="Alerts"
        text="No alerts yet — high-risk liquidity events will appear here."
      />
    );
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h3 className="panel-title">Alert Feed</h3>
        <p className="panel-sub">{total} WARNINGS</p>
      </div>

      <div>
        {[...alerts].reverse().map((alert, index) => (
          <div
            key={`alert-${alert.timestamp}-${index}`}
            className="flex gap-2 border-b border-noir-line px-3 py-2 last:border-0"
          >
            <span className="text-noir-blood blink" aria-hidden="true">
              ▸
            </span>
            <div className="min-w-0 flex-1">
              <div className="mb-0.5 flex items-center justify-between gap-2">
                <RiskBadge level={alert.level} />
                <span className="text-[10px] text-noir-dim">
                  {new Date(alert.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs text-noir-text">{alert.message}</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-wider text-noir-muted">
                Drain prob{" "}
                {alert.drain_probability != null
                  ? `${(alert.drain_probability * 100).toFixed(1)}%`
                  : "—"}{" "}
                · Impact {formatPct(alert.price_impact_pct)}
              </p>
            </div>
          </div>
        ))}

        {[...highRiskEvents].reverse().map((event, index) => (
          <div
            key={`event-${event.transaction_hash ?? ""}-${index}`}
            className="flex gap-2 border-b border-noir-line px-3 py-2 last:border-0"
          >
            <span className="text-noir-blood blink" aria-hidden="true">
              ▸
            </span>
            <div className="min-w-0 flex-1">
              <div className="mb-0.5 flex items-center justify-between gap-2">
                <RiskBadge level={event.prediction?.risk_level ?? "High"} />
                <span className="text-[10px] text-noir-dim">
                  {new Date(event.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs text-noir-text">
                Warning: {event.pair} pool is predicted to experience a{" "}
                {formatPct(event.prediction?.predicted_drain_percentage)}{" "}
                liquidity drain in the next 3 blocks with an estimated price
                impact of {formatPct(event.prediction?.predicted_price_impact)}.
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
