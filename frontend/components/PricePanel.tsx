"use client";

import { formatPrice, formatUsd, shortenAddress } from "@/lib/format";
import type { PoolState } from "@/lib/types";

interface PricePanelProps {
  pools: PoolState[];
}

export default function PricePanel({ pools }: PricePanelProps) {
  if (pools.length === 0) {
    return (
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h3 className="font-semibold text-slate-100">Pool Prices</h3>
        <p className="mt-4 text-sm text-slate-400">
          Waiting for snapshot data from the server…
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-6 py-4">
        <h3 className="font-semibold text-slate-100">Pool Prices</h3>
        <p className="text-xs text-slate-400">
          Live on-chain state for watched pools
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs uppercase text-slate-500">
              <th className="px-6 py-3 font-medium">Pool</th>
              <th className="px-6 py-3 font-medium">Price</th>
              <th className="px-6 py-3 font-medium">Fee</th>
              <th className="px-6 py-3 font-medium">Tick</th>
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
                  {pool.tvl_usd != null ? formatUsd(pool.tvl_usd) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
