"""Mempool watcher.

Subscribes to pending transactions and decodes Uniswap v3 swap calls. In mock
mode a synthetic generator feeds the same event queue, keeping the rest of the
pipeline identical.
"""
from __future__ import annotations

import logging
import queue
import random
import threading
import time

from eth_abi import decode as abi_decode

from ..core.config import Settings

logger = logging.getLogger(__name__)

# Known SwapRouter / SwapRouter02 selectors.
_SWAP_SELECTORS = {
    "0x414bf389": "exactInputSingle",   # (tuple, uint256)
    "0xdb3e2198": "exactOutputSingle",  # (tuple, uint256)
    "0xc04b8d59": "exactInput",         # (bytes, address, uint256, uint256, uint256)
    "0xf28c0498": "exactOutput",        # (bytes, address, uint256, uint256, uint256)
    "0xac9650d8": "multicall",          # (bytes[])
}

_EXACT_INPUT_SINGLE_TYPES = [
    "address", "address", "uint24", "address", "uint256", "uint256", "uint256", "uint160",
]


class MempoolWatcher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue: queue.Queue = queue.Queue(maxsize=10_000)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="mempool-watcher")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ #
    # Event consumption (called from the monitor task)
    # ------------------------------------------------------------------ #
    def drain_events(self) -> list[dict]:
        events: list[dict] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                return events

    # ------------------------------------------------------------------ #
    # Producers
    # ------------------------------------------------------------------ #
    def _run(self) -> None:
        if self._settings.mock_mode:
            self._run_mock()
        else:
            self._run_websocket()

    def _run_mock(self) -> None:
        rng = random.Random(42)
        while not self._stop.is_set():
            time.sleep(rng.uniform(1.0, 4.0))
            if not self._settings.watchlist:
                continue
            entry = rng.choice(self._settings.watchlist)
            event = {
                "type": "swap",
                "pool": entry["address"],
                "token_in": entry["token0"],
                "token_out": entry["token1"],
                "amount_in": rng.uniform(1e3, 5e5),
                "timestamp": int(time.time()),
            }
            self._put(event)

    def _run_websocket(self) -> None:
        try:
            from web3 import Web3

            w3 = Web3(Web3.WebsocketProvider(self._settings.rpc_url_ws))
            subscription = w3.eth.subscribe("newPendingTransactions")
            logger.info("Mempool subscription active (%s)", self._settings.rpc_url_ws)
            for tx_hash in subscription:
                if self._stop.is_set():
                    break
                try:
                    tx = w3.eth.get_transaction(tx_hash)
                except Exception:  # noqa: BLE001 - tx may disappear from the pool
                    continue
                event = self._decode_swap(tx)
                if event is not None:
                    self._put(event)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Mempool websocket terminated: %s", exc)

    # ------------------------------------------------------------------ #
    # Decoding
    # ------------------------------------------------------------------ #
    def _decode_swap(self, tx: dict) -> dict | None:
        data = tx.get("input") if isinstance(tx, dict) else None
        if not data or len(data) < 10:
            return None

        selector = data[:10]
        if selector not in _SWAP_SELECTORS:
            return None

        payload = data[10:]
        try:
            if selector == "0x414bf389":
                params = abi_decode(_EXACT_INPUT_SINGLE_TYPES, bytes.fromhex(payload))
                token_in, token_out = params[0], params[1]
                amount_in = int(params[5])
            elif selector == "0xdb3e2198":
                params = abi_decode(_EXACT_INPUT_SINGLE_TYPES, bytes.fromhex(payload))
                token_in, token_out = params[0], params[1]
                amount_in = int(params[5])
            else:
                # exactInput/exactOutput/multicall need nested decoding; keep the
                # signal but leave amounts unknown rather than misreporting.
                return {
                    "type": "swap",
                    "pool": None,
                    "token_in": None,
                    "token_out": None,
                    "amount_in": None,
                    "selector": _SWAP_SELECTORS[selector],
                    "to": tx.get("to"),
                    "timestamp": int(time.time()),
                }
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to decode tx: %s", exc)
            return None

        return {
            "type": "swap",
            "pool": None,
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": amount_in,
            "selector": _SWAP_SELECTORS[selector],
            "to": tx.get("to"),
            "timestamp": int(time.time()),
        }

    def _put(self, event: dict) -> None:
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass
