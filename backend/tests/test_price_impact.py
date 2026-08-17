"""Unit tests for the Uniswap v3 price-impact math.

The math mirrors the core contracts, so these guard against regressions even
without a node.
"""
from __future__ import annotations

import math

import pytest

from app.services.price_impact import (
    Q96,
    get_amount0_out,
    get_amount1_out,
    get_next_sqrt_price_one_for_zero,
    get_next_sqrt_price_zero_for_one,
    human_price,
)


def _sqrt_price_x96(human_price_value: float, decimals0: int, decimals1: int) -> int:
    """Build sqrtPriceX96 from a human price of token0 denominated in token1."""
    raw_price = human_price_value / (10 ** (decimals0 - decimals1))
    return int(math.sqrt(raw_price) * Q96)


def test_human_price_recovers_input_price():
    sp = _sqrt_price_x96(3000.0, 18, 6)
    assert abs(human_price(sp, 18, 6) - 3000.0) < 1e-6


def test_human_price_stable_quote():
    sp = _sqrt_price_x96(0.0003, 6, 18)  # USDC/WETH: WETH per USDC
    assert abs(human_price(sp, 6, 18) - 0.0003) < 1e-9


def test_zero_for_one_decreases_price_and_emits_token1():
    sp = _sqrt_price_x96(3000.0, 18, 6)
    liquidity = 10**18
    amount0_in = 10**18  # 1 WETH
    sp_new = get_next_sqrt_price_zero_for_one(sp, liquidity, amount0_in)
    assert sp_new < sp
    assert get_amount1_out(sp, sp_new, liquidity) > 0


def test_one_for_zero_increases_price_and_emits_token0():
    sp = _sqrt_price_x96(3000.0, 18, 6)
    liquidity = 10**18
    amount1_in = 3000 * 10**6  # 3000 USDC
    sp_new = get_next_sqrt_price_one_for_zero(sp, liquidity, amount1_in)
    assert sp_new > sp
    assert get_amount0_out(sp, sp_new, liquidity) > 0


def test_small_trade_has_small_impact():
    sp = _sqrt_price_x96(3000.0, 18, 6)
    liquidity = 10**18
    small_in = 10**18  # 1 WETH
    sp_new = get_next_sqrt_price_zero_for_one(sp, liquidity, small_in)
    impact = ((sp_new / Q96) ** 2 - (sp / Q96) ** 2) / (sp / Q96) ** 2
    assert abs(impact) < 0.01


def test_zero_liquidity_rejected():
    with pytest.raises(ValueError):
        get_next_sqrt_price_zero_for_one(_sqrt_price_x96(3000.0, 18, 6), 0, 10**18)
