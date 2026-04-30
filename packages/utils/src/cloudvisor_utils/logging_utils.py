"""Structured logging configuration for CloudVisor services."""

import logging
import sys
from typing import Any


def configure_logging(service_name: str = "cloudvisor", log_level: str = "INFO") -> None:
    """Configure standard JSON-style logging."""
    log_level_val = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format=f"%(levelname)s:%(name)s:%(message)s",
        stream=sys.stdout,
        level=log_level_val,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a standard Python logger."""
    return logging.getLogger(name or "cloudvisor")
