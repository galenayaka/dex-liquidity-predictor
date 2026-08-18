"use client";

import EmptyPanel from "@/components/EmptyPanel";
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
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-6 py-4">
        <h3 className="font-semibold text-slate-100">Prediction History</h3>
        <p className="text-xs text-slate-400">
          Latest {recent.length} on-chain events
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs uppercase text-slate-500">
              <th className="px-6 py-3 font-medium">Time</th>
              <th className="px-6 py-3 font-medium">Event</th>
              <th className="px-6 py-3 font-medium">Pair</th>
              <th className="px-6 py-3 font-medium">Drain</th>
              <th className="px-6 py-3 font-medium">Impact</th>
              <th className="px-6 py-3 font-medium">Risk</th>
              <th className="px-6 py-3 font-medium">Tx</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((event, index) => (
              <tr
                key={`${event.transaction_hash ?? "tx"}-${index}`}
                className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30"
              >
                <td className="px-6 py-3 text-slate-300">
                  {new Date(event.timestamp * 1000).toLocaleTimeString()}
                </td>
                <td className="px-6 py-3 text-slate-200">{event.event}</td>
                <td className="px-6 py-3 text-slate-200">{event.pair}</td>
                <td className="px-6 py-3 text-red-300">
                  {formatPct(event.prediction?.predicted_drain_percentage)}
                </td>
                <td className="px-6 py-3 text-slate-200">
                  {formatPct(event.prediction?.predicted_price_impact)}
                </td>
                <td className="px-6 py-3">
                  {event.prediction ? (
                    <RiskBadge level={event.prediction.risk_level} />
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-6 py-3 font-mono text-xs text-slate-500">
                  {shortenAddress(event.transaction_hash)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
