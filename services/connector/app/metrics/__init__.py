"""Prometheus metrics module."""

from .prometheus import ConnectorMetrics, connector_last_sync_age_seconds

__all__ = [
    "ConnectorMetrics",
    "connector_last_sync_age_seconds",
]
