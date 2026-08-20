/**
 * LiquidityChart — TradingView lightweight-charts area chart.
 *
 * The chart is created once on mount and updated imperatively via
 * `series.update()` (only new points are pushed), so React does not re-render
 * on every tick. A ResizeObserver keeps the width in sync, and the theme
 * effect re-reads CSS variables to restyle the chart when the accent changes.
 */
"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "@/components/ThemeProvider";
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
  /** Render the surrounding bordered panel (disable when nested). */
  bordered?: boolean;
  height?: number;
}

function toPoint(point: LiquidityPoint): { time: UTCTimestamp; value: number } {
  return { time: point.time as UTCTimestamp, value: point.value };
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const num = parseInt(full, 16);
  if (Number.isNaN(num)) return `rgba(255, 153, 0, ${alpha})`;
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function readAccentColors(): { accent: string; muted: string } {
  const cs = getComputedStyle(document.documentElement);
  return {
    accent: cs.getPropertyValue("--noir-accent2").trim() || "#FF9900",
    muted: cs.getPropertyValue("--noir-muted").trim() || "#c28f3a",
  };
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
  subtitle = "Raw liquidity ×10¹⁸",
  live = true,
  bordered = true,
  height = 280,
}: LiquidityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const appliedRef = useRef(0);
  const { theme } = useTheme();

  // Create the chart + series once on mount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const { accent, muted } = readAccentColors();

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: muted,
        fontSize: 10,
        fontFamily: "'JetBrains Mono', 'Roboto Mono', monospace",
      },
      grid: {
        vertLines: { color: hexToRgba(accent, 0.06) },
        horzLines: { color: hexToRgba(accent, 0.06) },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: hexToRgba(accent, 0.25),
      },
      timeScale: {
        borderColor: hexToRgba(accent, 0.25),
        timeVisible: true,
        secondsVisible: false,
      },
      localization: {
        priceFormatter: (price: number) =>
          Math.abs(price) >= 1000
            ? price.toLocaleString(undefined, { maximumFractionDigits: 0 })
            : price.toFixed(3),
      },
    });

    const series = chart.addAreaSeries({
      lineColor: accent,
      topColor: hexToRgba(accent, 0.32),
      bottomColor: hexToRgba(accent, 0.01),
      lineWidth: 1,
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

  // Re-apply accent colors when the UI theme changes.
  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series) return;
    const { accent, muted } = readAccentColors();
    chart.applyOptions({
      layout: { textColor: muted },
      grid: {
        vertLines: { color: hexToRgba(accent, 0.06) },
        horzLines: { color: hexToRgba(accent, 0.06) },
      },
      rightPriceScale: { borderColor: hexToRgba(accent, 0.25) },
      timeScale: { borderColor: hexToRgba(accent, 0.25) },
    });
    series.applyOptions({
      lineColor: accent,
      topColor: hexToRgba(accent, 0.32),
      bottomColor: hexToRgba(accent, 0.01),
    });
  }, [theme]);

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
    <section className={bordered ? "panel p-2" : "p-2"}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <div>
          <h3 className="panel-title">{title}</h3>
          <p className="panel-sub">{subtitle}</p>
        </div>
        {live && (
          <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-noir-amber">
            <span
              className="h-2 w-2 animate-pulse rounded-full bg-noir-orange dot-glow"
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
