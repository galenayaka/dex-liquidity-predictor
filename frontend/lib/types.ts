// TypeScript models mirroring the FastAPI backend's Pydantic schemas and the
// JSON messages broadcast over the `/ws` WebSocket channel.

export type RiskLevel = "Low" | "Medium" | "High";

export type AlertLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface TokenMeta {
  address: string;
  symbol: string;
  decimals: number;
}

export interface PoolState {
  address: string;
  token0: TokenMeta;
  token1: TokenMeta;
  fee: number; // fee tier in hundredths of a bip (e.g. 3000 -> 0.3%)
  liquidity: number; // current in-range liquidity (Q128)
  sqrt_price_x96: number; // Q64.96 encoded sqrt price
  tick: number;
  price: number; // human price of token0 denominated in token1
  tvl_usd?: number | null;
  timestamp?: number | null;
}

export interface Prediction {
  predicted_drain_percentage: number; // 0..100
  predicted_price_impact: number; // 0..100 (percent)
  risk_level: RiskLevel;
}

/** Broadcast by the Swap/Burn event listener (`type: "event"`). */
export interface EventMessage {
  type: "event";
  event: "Swap" | "Burn";
  pool: string;
  pair: string;
  transaction_hash?: string | null;
  block_number?: number | null;
  args: Record<string, unknown>;
  prediction?: Prediction | null;
  raw?: Record<string, unknown>;
  timestamp: number;
}

/** Broadcast by the monitor loop (`type: "alert"`). */
export interface AlertMessage {
  type: "alert";
  level: AlertLevel;
  pool_address: string;
  pair: string;
  message: string;
  drain_probability?: number | null;
  liquidity_change_pct?: number | null;
  price_impact_pct?: number | null;
  timestamp: number;
}

/** Sent once on connect (`type: "snapshot"`). */
export interface SnapshotMessage {
  type: "snapshot";
  data: PoolState[];
}

export type WSMessage = EventMessage | AlertMessage | SnapshotMessage;
