"use client";

import type { ReactNode } from "react";
import Explain from "@/components/Explain";
import RiskBadge from "@/components/RiskBadge";
import { formatPct, shortenAddress } from "@/lib/format";
import type { AlertMessage, EventMessage } from "@/lib/types";

interface PredictionPanelProps {
  event: EventMessage | null;
  alert: AlertMessage | null;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-noir-line py-1 last:border-0">
      <span className="text-[10px] uppercase tracking-[0.14em] text-noir-dim">
        {label}
      </span>
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
    <section className="panel">
      <div className="panel-head">
        <h3 className="panel-title">Liquidity Prediction</h3>
        <p className="panel-sub">Latest event inference</p>
      </div>

      <div className="px-3 py-2">
        {prediction ? (
          <div>
            <Row label="Event">
              <span className="text-xs font-bold text-noir-amber">
                {event?.event} · {event?.pair}
              </span>
            </Row>
            <Row label="Risk level">
              <RiskBadge level={prediction.risk_level} />
            </Row>
            <Row label="Drain prediction">
              <span className="text-xs font-bold text-noir-orange">
                {formatPct(prediction.predicted_drain_percentage)}
              </span>
            </Row>
            <Row label="Price impact">
              <span className="text-xs font-bold text-noir-text">
                {formatPct(prediction.predicted_price_impact)}
              </span>
            </Row>
            {event?.transaction_hash && (
              <Row label="Transaction">
                <span className="text-[10px] text-noir-dim">
                  {shortenAddress(event.transaction_hash)}
                </span>
              </Row>
            )}
          </div>
        ) : (
          <p className="py-2 text-xs uppercase tracking-wider text-noir-dim">
            No prediction yet — waiting for events…
          </p>
        )}

        {alert && (
          <div className="mt-2 border-t border-noir-line pt-2">
            <RiskBadge level={alert.level} />
            <p className="mt-1 text-xs text-noir-text">{alert.message}</p>
            <p className="mt-1 text-[10px] uppercase tracking-wider text-noir-muted">
              Drain prob{" "}
              {alert.drain_probability != null
                ? `${(alert.drain_probability * 100).toFixed(1)}%`
                : "—"}{" "}
              · Impact {formatPct(alert.price_impact_pct)}
            </p>
          </div>
        )}
      </div>

      <Explain title="What this means">
        "Drain" is the predicted % of liquidity likely to leave the pool soon.
        "Price impact" is how much a typical trade would move the price. Higher
        numbers mean more risk — the risk level (Low / Medium / High) summarises
        both.
      </Explain>
    </section>
  );
}
