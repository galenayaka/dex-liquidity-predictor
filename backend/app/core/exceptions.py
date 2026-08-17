"""Application-level exceptions mapped to HTTP responses."""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base error carrying an HTTP status code and a machine-readable code."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class InvalidAddressError(AppError):
    status_code = 400
    code = "invalid_address"


class Web3ConnectionError(AppError):
    status_code = 503
    code = "web3_unavailable"


class PriceImpactError(AppError):
    status_code = 422
    code = "invalid_swap"


class PredictionError(AppError):
    status_code = 500
    code = "prediction_failed"
