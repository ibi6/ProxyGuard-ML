"""Central logging setup for ProxyGuard ML."""

from __future__ import annotations

import logging
import os
import sys


def setup_logging(level: str | None = None) -> None:
    """Configure root logger once (safe to call from lifespan)."""
    name = level or os.getenv("LOG_LEVEL", "INFO")
    numeric = getattr(logging, name.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(numeric)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(numeric)
    # Quiet noisy third-party loggers in demo mode
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
