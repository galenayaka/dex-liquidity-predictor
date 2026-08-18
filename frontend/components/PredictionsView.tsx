"use client";

import EmptyPanel from "@/components/EmptyPanel";
import Explain from "@/components/Explain";
import RiskBadge from "@/components/RiskBadge";
import { formatPct, shortenAddress } from "@/lib/format";
import type { EventMessage } from "@/lib/types";

export default function PredictionsView({
  events,
}: {
  events: EventMessage[];
}) {
  if (events.length === 0) {
    return (
      <EmptyPanel
        title="Predictions"
        text="No predictions yet — waiting for Swap/Burn events…"
      />
    );
  }

  const recent = [...events].reverse();

  return (
    <section className="panel overflow-hidden">
      <div className="panel-head">
        <h3 className="panel-title">Prediction Feed</h3>
        <p className="panel-sub">{recent.length} EVENTS</p>
      </div>
      <div className="overflow-x-auto">
        <table className="tbl">
          <thead>
            <tr>
              <th>Time</th>
              <th className="text-left">Event</th>
              <th className="text-left">Pair</th>
              <th>Drain%</th>
              <th>Impact%</th>
              <th>Risk</th>
              <th className="text-left">Tx</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((event, index) => (
              <tr key={`${event.transaction_hash ?? "tx"}-${index}`}>
                <td className="text-noir-dim">
                  {new Date(event.timestamp * 1000).toLocaleTimeString()}
                </td>
                <td className="text-left text-noir-amber">{event.event}</td>
                <td className="text-left">{event.pair}</td>
                <td className="text-noir-orange">
                  {formatPct(event.prediction?.predicted_drain_percentage)}
                </td>
                <td>{formatPct(event.prediction?.predicted_price_impact)}</td>
                <td>
                  {event.prediction ? (
                    <RiskBadge level={event.prediction.risk_level} />
                  ) : (
                    <span className="text-noir-dim">—</span>
                  )}
                </td>
                <td className="text-left text-[10px] text-noir-dim">
                  {shortenAddress(event.transaction_hash)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Explain title="Reading the prediction feed">
        Each row is a live on-chain event. <b>Swap</b> means a trade happened;
        <b>Burn</b> means someone withdrew liquidity — the main warning sign. The
        AI then estimates the drain % and price impact, and tags a risk level.
      </Explain>
    </section>
  );
}
