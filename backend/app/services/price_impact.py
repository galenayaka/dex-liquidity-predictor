"""Uniswap v3 price-impact math and quote service.

All math uses raw integer units (wei / Q64.96) exactly like the Uniswap v3
core contracts, so results are overflow-safe and unit-testable without a node.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..schemas.pool import PoolState

Q96 = 2**96

STABLES = {"USDC", "USDT", "DAI", "BUSD", "TUSD", "FRAX", "GUSD", "USD"}


# --------------------------------------------------------------------------- #
# Pure math helpers
# --------------------------------------------------------------------------- #
def sqrt_price_x96_to_raw_price(sqrt_price_x96: int) -> float:
    """Raw price = amount(token1) per amount(token0), both in raw units."""
    return (sqrt_price_x96 / Q96) ** 2


def human_price(sqrt_price_x96: int, decimals0: int, decimals1: int) -> float:
    """Human price of token0 denominated in token1."""
    raw = sqrt_price_x96_to_raw_price(sqrt_price_x96)
    return raw * (10 ** (decimals0 - decimals1))


def get_next_sqrt_price_zero_for_one(
    sqrt_price_x96: int, liquidity: int, amount0_in: int
) -> int:
    """Exact-input swap token0 -> token1; price moves down."""
    if sqrt_price_x96 <= 0 or liquidity <= 0 or amount0_in <= 0:
        raise ValueError("sqrt_price_x96, liquidity and amount0_in must be positive")
    numerator = sqrt_price_x96 * liquidity * Q96
    denominator = liquidity * Q96 + amount0_in * sqrt_price_x96
    return numerator // denominator


def get_next_sqrt_price_one_for_zero(
    sqrt_price_x96: int, liquidity: int, amount1_in: int
) -> int:
    """Exact-input swap token1 -> token0; price moves up."""
    if sqrt_price_x96 <= 0 or liquidity <= 0 or amount1_in <= 0:
        raise ValueError("sqrt_price_x96, liquidity and amount1_in must be positive")
    return sqrt_price_x96 + (amount1_in * Q96) // liquidity


def get_amount0_out(sqrt_price_old: int, sqrt_price_new: int, liquidity: int) -> int:
    """token0 out for a price increase (token1 -> token0)."""
    if sqrt_price_new <= sqrt_price_old:
        return 0
    return (
        liquidity * Q96 * (sqrt_price_new - sqrt_price_old)
    ) // (sqrt_price_old * sqrt_price_new)


def get_amount1_out(sqrt_price_old: int, sqrt_price_new: int, liquidity: int) -> int:
    """token1 out for a price decrease (token0 -> token1)."""
    if sqrt_price_old <= sqrt_price_new:
        return 0
    return (liquidity * (sqrt_price_old - sqrt_price_new)) // Q96


@dataclass
class SwapQuote:
    pool_address: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_before: float
    price_after: float
    price_impact_pct: float


class PriceImpactService:
    """Simulates an exact-input swap and computes its price impact."""

    def quote(self, pool: PoolState, token_in: str, amount_in: float) -> SwapQuote:
        if amount_in <= 0:
            raise ValueError("amount_in must be positive")

        token_in = token_in.lower()
        token0, token1 = pool.token0, pool.token1
        sp = pool.sqrt_price_x96
        liquidity = pool.liquidity

        if token_in == token0.address.lower():
            # Sell token0, receive token1.
            raw_in = int(amount_in * (10**token0.decimals))
            sp_new = get_next_sqrt_price_zero_for_one(sp, liquidity, raw_in)
            raw_out = get_amount1_out(sp, sp_new, liquidity)
            token_out = token1
            out_decimals = token1.decimals
            price_before = human_price(sp, token0.decimals, token1.decimals)
            price_after = human_price(sp_new, token0.decimals, token1.decimals)
        elif token_in == token1.address.lower():
            # Sell token1, receive token0.
            raw_in = int(amount_in * (10**token1.decimals))
            sp_new = get_next_sqrt_price_one_for_zero(sp, liquidity, raw_in)
            raw_out = get_amount0_out(sp, sp_new, liquidity)
            token_out = token0
            out_decimals = token0.decimals
            price_before = 1.0 / human_price(sp, token0.decimals, token1.decimals)
            price_after = 1.0 / human_price(sp_new, token0.decimals, token1.decimals)
        else:
            raise ValueError("token_in is not part of this pool")

        amount_out = raw_out / (10**out_decimals)
        impact = ((price_after - price_before) / price_before * 100.0) if price_before else 0.0

        return SwapQuote(
            pool_address=pool.address,
            token_in=token0.address if token_in == token0.address.lower() else token1.address,
            token_out=token_out.address,
            amount_in=amount_in,
            amount_out=amount_out,
            price_before=price_before,
            price_after=price_after,
            price_impact_pct=impact,
        )

    def quote_usd(self, pool: PoolState, usd_amount: float) -> SwapQuote | None:
        """Quote a reference trade of roughly `usd_amount` USD.

        We pick the non-stable token as the traded asset so the reference size
        is meaningful regardless of which side is the quote currency.
        """
        if pool.price <= 0:
            return None
        if self._is_stable(pool.token1.symbol):
            token_in = pool.token0.address
            amount_in = usd_amount / pool.price
        elif self._is_stable(pool.token0.symbol):
            token_in = pool.token1.address
            amount_in = usd_amount * pool.price
        else:
            token_in = pool.token0.address
            amount_in = usd_amount / pool.price
        return self.quote(pool, token_in, amount_in)

    @staticmethod
    def _is_stable(symbol: str) -> bool:
        return symbol.upper() in STABLES
