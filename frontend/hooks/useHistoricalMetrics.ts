"use client";

import { useEffect, useState } from "react";
import type { LiquidityPoint } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type TimeRange = "1h" | "24h" | "7d";

interface UseHistoricalMetricsResult {
  points: LiquidityPoint[];
  loading: boolean;
  error: string | null;
}

/**
 * Fetch historical liquidity metrics from `GET /api/v1/metrics/{pool}` so the
 * chart can be seeded before the WebSocket live feed takes over.
 */
export function useHistoricalMetrics(
  poolAddress: string | null,
  timeRange: TimeRange = "24h",
): UseHistoricalMetricsResult {
  const [points, setPoints] = useState<LiquidityPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!poolAddress) {
      setPoints([]);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    // Reset the previous pool's points so the chart remounts cleanly instead
    // of trying to append a different pool's series (which crashes
    // lightweight-charts when timestamps go backwards).
    setPoints([]);

    const url = `${API_URL}/api/v1/metrics/${encodeURIComponent(
      poolAddress,
    )}?time_range=${timeRange}`;

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<LiquidityPoint[]>;
      })
      .then((data) => {
        if (!cancelled) setPoints(data);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setPoints([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [poolAddress, timeRange]);

  return { points, loading, error };
}
