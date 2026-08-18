"use client";

import { formatPct } from "@/lib/format";
import type { AlertMessage, EventMessage } from "@/lib/types";

interface AlertBannerProps {
  event: EventMessage | null;
  alert: AlertMessage | null;
}

/**
 * Severe high-contrast banner shown when the real-time stream reports a
 * high-risk liquidity event (`risk_level === "High"`) or a HIGH/CRITICAL alert.
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
      className="flex items-center gap-3 border border-noir-blood bg-noir-panel2 px-3 py-2"
    >
      <span className="text-noir-blood blink" aria-hidden="true">
        ⚠
      </span>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-noir-blood">
          High-risk liquidity alert
        </p>
        <p className="truncate text-xs text-noir-text">{message}</p>
      </div>
    </div>
  );
}
