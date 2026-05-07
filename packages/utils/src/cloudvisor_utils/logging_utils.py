"""Structured JSON logging configuration for CloudVisor services.

Every service emits structured JSON logs to stdout per spec Rule 9:
  - correlation_id
  - organization_id
  - service_name
  - level
"""

import json
import logging
import sys
import time
from typing import Any


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.
    Required fields per spec: correlation_id, organization_id, service_name, level.
    """

    def __init__(self, service_name: str = "cloudvisor") -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt=None),
            "level": record.levelname,
            "service_name": self._service_name,
            "logger": record.name,
            "message": record.getMessage(),
            # Optional context fields — populated via LoggerAdapter or extra={}
            "correlation_id": getattr(record, "correlation_id", None),
            "organization_id": getattr(record, "organization_id", None),
        }

        # Remove None values to keep logs clean
        log_obj = {k: v for k, v in log_obj.items() if v is not None}

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def configure_logging(service_name: str = "cloudvisor", log_level: str = "INFO") -> None:
    """Configure structured JSON logging to stdout per spec Rule 9."""
    log_level_val = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter(service_name=service_name))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_val)
    # Remove any existing handlers to avoid duplicate output
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a standard Python logger."""
    return logging.getLogger(name or "cloudvisor")
