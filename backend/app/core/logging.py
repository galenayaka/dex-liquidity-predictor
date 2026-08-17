"""Centralised logging configuration."""
from __future__ import annotations

import logging
import sys


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stdout, force=True)

    # Third-party libraries are noisy at INFO; keep them quiet.
    for noisy in ("web3", "websockets", "urllib3", "httpx", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
