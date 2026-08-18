"use client";

import { useState } from "react";
import EmptyPanel from "@/components/EmptyPanel";
import LiquidityChart from "@/components/LiquidityChart";
import { useHistoricalMetrics } from "@/hooks/useHistoricalMetrics";
import { formatPrice, formatUsd, shortenAddress } from "@/lib/format";
import type { PoolState } from "@/lib/types";

export default function PoolsView({ pools }: { pools: PoolState[] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const activeAddress = selected ?? pools[0]?.address ?? null;
  const { points, loading, error } = useHistoricalMetrics(activeAddress, "24h");

  if (pools.length === 0) {
    return (
      <EmptyPanel
        title="Pools"
        text="Waiting for pool data from the server…"
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-6 py-4">
          <h3 className="font-semibold text-slate-100">Watched Pools</h3>
          <p className="text-xs text-slate-400">Live on-chain state</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase text-slate-500">
                <th className="px-6 py-3 font-medium">Pool</th>
                <th className="px-6 py-3 font-medium">Price</th>
                <th className="px-6 py-3 font-medium">Fee</th>
                <th className="px-6 py-3 font-medium">Tick</th>
                <th className="px-6 py-3 font-medium">Liquidity</th>
                <th className="px-6 py-3 font-medium">TVL</th>
              </tr>
            </thead>
            <tbody>
              {pools.map((pool) => (
                <tr
                  key={pool.address}
                  className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30"
                >
                  <td className="px-6 py-3">
                    <div className="font-medium text-slate-100">
                      {pool.token0.symbol}/{pool.token1.symbol}
                    </div>
                    <div className="text-xs text-slate-500">
                      {shortenAddress(pool.address)}
                    </div>
                  </td>
                  <td className="px-6 py-3 text-slate-200">
                    {formatPrice(pool.price)}
                  </td>
                  <td className="px-6 py-3 text-slate-200">
                    {(pool.fee / 10000).toFixed(2)}%
                  </td>
                  <td className="px-6 py-3 text-slate-200">{pool.tick}</td>
                  <td className="px-6 py-3 text-slate-200">
                    {pool.liquidity.toLocaleString()}
                  </td>
                  <td className="px-6 py-3 text-slate-200">
                    {pool.tvl_usd != null ? formatUsd(pool.tvl_usd) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-slate-100">
              Historical Liquidity
            </h3>
            <p className="text-xs text-slate-400">
              Last 24 hours · token A reserve (USD)
            </p>
          </div>
          <select
            value={activeAddress ?? ""}
            onChange={(event) => setSelected(event.target.value)}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none"
          >
            {pools.map((pool) => (
              <option key={pool.address} value={pool.address}>
                {pool.token0.symbol}/{pool.token1.symbol}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <p className="mb-4 text-sm text-amber-300">
            Historical data unavailable — start the backend (and PostgreSQL) to
            populate metrics.
          </p>
        )}

        {loading && points.length === 0 ? (
          <p className="text-sm text-slate-500">Loading historical data…</p>
        ) : (
          <LiquidityChart
            data={points}
            title="Historical Liquidity (24h)"
            subtitle="token A reserve (USD)"
            live={false}
          />
        )}
      </section>
    </div>
  );
}
