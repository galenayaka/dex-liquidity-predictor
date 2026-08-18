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
      <EmptyPanel title="Pools" text="Awaiting pool data from server…" />
    );
  }

  return (
    <div className="space-y-3">
      <section className="panel overflow-hidden">
        <div className="panel-head">
          <h3 className="panel-title">Watched Pools</h3>
          <p className="panel-sub">Live on-chain state</p>
        </div>
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr>
                <th>Pool</th>
                <th>Price</th>
                <th>Fee</th>
                <th>Tick</th>
                <th>Liquidity</th>
                <th>TVL</th>
              </tr>
            </thead>
            <tbody>
              {pools.map((pool) => (
                <tr key={pool.address}>
                  <td>
                    <div className="text-noir-amber">
                      {pool.token0.symbol}/{pool.token1.symbol}
                    </div>
                    <div className="text-[10px] text-noir-dim">
                      {shortenAddress(pool.address)}
                    </div>
                  </td>
                  <td>{formatPrice(pool.price)}</td>
                  <td>{(pool.fee / 10000).toFixed(2)}%</td>
                  <td>{pool.tick}</td>
                  <td>{pool.liquidity.toLocaleString()}</td>
                  <td>
                    {pool.tvl_usd != null ? formatUsd(pool.tvl_usd) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="panel-head">
          <div>
            <h3 className="panel-title">Historical Liquidity</h3>
            <p className="panel-sub">Last 24h · Token A reserve (USD)</p>
          </div>
          <select
            value={activeAddress ?? ""}
            onChange={(event) => setSelected(event.target.value)}
            className="border border-noir-line bg-black px-2 py-1 text-xs uppercase tracking-wider text-noir-amber focus:outline-none"
          >
            {pools.map((pool) => (
              <option key={pool.address} value={pool.address}>
                {pool.token0.symbol}/{pool.token1.symbol}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <p className="border-b border-noir-line bg-noir-panel2 px-2 py-1 text-xs text-noir-muted">
            Historical data unavailable — start backend + PostgreSQL
          </p>
        )}

        {loading && points.length === 0 ? (
          <p className="px-2 py-4 text-xs uppercase tracking-wider text-noir-dim">
            Loading historical data…
          </p>
        ) : (
          <LiquidityChart
            data={points}
            title="Historical Liquidity"
            subtitle="Token A reserve (USD)"
            live={false}
            bordered={false}
          />
        )}
      </section>
    </div>
  );
}
