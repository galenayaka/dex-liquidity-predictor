"use client";

import Explain from "@/components/Explain";
import { formatPrice, formatUsd, shortenAddress } from "@/lib/format";
import type { PoolState } from "@/lib/types";

export default function PricePanel({ pools }: { pools: PoolState[] }) {
  if (pools.length === 0) {
    return (
      <section className="panel p-4">
        <h3 className="text-xs font-bold uppercase tracking-[0.18em] text-noir-amber">
          Pool Prices
        </h3>
        <p className="mt-2 text-xs uppercase tracking-wider text-noir-dim">
          Awaiting snapshot data from server…
        </p>
      </section>
    );
  }

  return (
    <section className="panel overflow-hidden">
      <div className="panel-head">
        <h3 className="panel-title">Pool Prices</h3>
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
                <td>{pool.tvl_usd != null ? formatUsd(pool.tvl_usd) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Explain title="Reading this table">
        TVL is the total money locked in the pool — bigger usually means
        healthier. Price is the current exchange rate between the two tokens, and
        Fee is what each swap costs. Tick is a technical price-range marker; you
        can safely ignore it.
      </Explain>
    </section>
  );
}
