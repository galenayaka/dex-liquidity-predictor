"use client";

import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { LiquidityPoint } from "@/lib/types";

interface LiquidityChartProps {
  /** Append-only time series; only new points are pushed into the chart. */
  data: LiquidityPoint[];
  title?: string;
  subtitle?: string;
  /** Show the pulsing "Live" badge (disable for historical views). */
  live?: boolean;
  height?: number;
}

function toPoint(point: LiquidityPoint): { time: UTCTimestamp; value: number } {
  return { time: point.time as UTCTimestamp, value: point.value };
}

/**
 * Real-time liquidity line/area chart powered by TradingView lightweight-charts.
 *
 * The chart instance is created exactly once and updated imperatively via
 * `series.update(...)` when the `data` prop grows, so the surrounding React
 * tree never has to re-render on every tick.
 */
export default function LiquidityChart({
  data,
  title = "Pool Liquidity",
  subtitle = "Real-time pool liquidity movements (×10¹⁸)",
  live = true,
  height = 280,
}: LiquidityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const appliedRef = useRef(0);

  // Create the chart + series once on mount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.08)" },
        horzLines: { color: "rgba(148, 163, 184, 0.08)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: "rgba(148, 163, 184, 0.25)",
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.25)",
        timeVisible: true,
        secondsVisible: false,
      },
      localization: {
        priceFormatter: (price: number) => price.toFixed(3),
      },
    });

    const series = chart.addAreaSeries({
      lineColor: "#38bdf8",
      topColor: "rgba(56, 189, 248, 0.35)",
      bottomColor: "rgba(56, 189, 248, 0.02)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    appliedRef.current = 0;

    const handleResize = () => {
      chart.applyOptions({ width: container.clientWidth });
    };
    const observer = new ResizeObserver(handleResize);
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
    // The chart is intentionally created only once; height changes are handled
    // by the dedicated effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the chart's height in sync with the prop without recreating it.
  useEffect(() => {
    chartRef.current?.applyOptions({ height });
  }, [height]);

  // Push only the newly arrived points into the series (in-place update).
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    if (appliedRef.current === 0) {
      if (data.length > 0) {
        series.setData(data.map(toPoint));
        appliedRef.current = data.length;
      }
      return;
    }

    for (let i = appliedRef.current; i < data.length; i++) {
      series.update(toPoint(data[i]));
    }
    appliedRef.current = data.length;
  }, [data]);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-100">{title}</h3>
          <p className="text-xs text-slate-400">{subtitle}</p>
        </div>
        {live && (
          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-300">
            <span
              className="h-2 w-2 animate-pulse rounded-full bg-emerald-400"
              aria-hidden="true"
            />
            Live
          </span>
        )}
      </div>
      <div ref={containerRef} style={{ height }} className="w-full" />
    </section>
  );
}
