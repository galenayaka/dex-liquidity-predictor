"""Singleton Web3 provider manager.

The backend is strictly read-only: no accounts or private keys are ever
attached to the provider.
"""
from __future__ import annotations

import logging

from web3 import Web3

from ..core.config import Settings, get_settings
from ..core.exceptions import InvalidAddressError, Web3ConnectionError

logger = logging.getLogger(__name__)


class Web3Client:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._w3: Web3 | None = None

    @property
    def w3(self) -> Web3:
        if self._w3 is None:
            self._w3 = Web3(
                Web3.HTTPProvider(
                    self._settings.rpc_url_http,
                    request_kwargs={"timeout": self._settings.request_timeout_seconds},
                )
            )
        return self._w3

    def is_connected(self) -> bool:
        if self._settings.mock_mode:
            return True
        try:
            return bool(self.w3.is_connected())
        except Exception as exc:  # noqa: BLE001 - any transport error => not connected
            logger.warning("Web3 connectivity check failed: %s", exc)
            return False

    def ensure_connected(self) -> Web3:
        if not self.is_connected():
            raise Web3ConnectionError(
                "Unable to reach the configured RPC endpoint. "
                "Check RPC_URL_HTTP or enable MOCK_MODE=true."
            )
        return self.w3

    def validate_address(self, address: str) -> str:
        """Return a checksummed address or raise."""
        if not address:
            raise InvalidAddressError("Address is required")
        try:
            return Web3.to_checksum_address(address)
        except Exception as exc:  # noqa: BLE001
            raise InvalidAddressError(f"Invalid Ethereum address: {address}") from exc


_client: Web3Client | None = None


def get_web3_client() -> Web3Client:
    global _client
    if _client is None:
        _client = Web3Client(get_settings())
    return _client
