"use client";

import { formatPct } from "@/lib/format";
import type { AlertMessage, EventMessage } from "@/lib/types";

interface AlertBannerProps {
  event: EventMessage | null;
  alert: AlertMessage | null;
}

/**
 * Red warning banner shown when the real-time stream reports a high-risk
 * liquidity event:
 *   - an `event` frame whose `prediction.risk_level` is "High", or
 *   - an `alert` frame at HIGH / CRITICAL level.
 */
export default function AlertBanner({ event, alert }: AlertBannerProps) {
  const prediction = event?.prediction;
  const highRiskEvent = prediction?.risk_level === "High";
  const highRiskAlert =
    alert != null && (alert.level === "HIGH" || alert.level === "CRITICAL");

  if (!highRiskEvent && !highRiskAlert) {
    return null;
  }

  const pair = event?.pair ?? alert?.pair ?? "ETH/USDC";
  const message = highRiskEvent
    ? `Warning: ${pair} pool is predicted to experience a ${formatPct(
        prediction?.predicted_drain_percentage,
      )} liquidity drain in the next 3 blocks with an estimated price impact of ${formatPct(
        prediction?.predicted_price_impact,
      )}`
    : alert?.message ?? "High-risk liquidity event detected";

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3"
    >
      <span className="text-lg leading-none" aria-hidden="true">
        ⚠️
      </span>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-red-300">
          High-risk liquidity alert
        </p>
        <p className="text-sm text-red-200/90">{message}</p>
      </div>
    </div>
  );
}
