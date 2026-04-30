"""
Shared Prometheus metrics utilities.
Every service exposes /metrics per spec Rule 9.
"""

import time
import logging
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info,
        generate_latest, CONTENT_TYPE_LATEST,
        CollectorRegistry, REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed — /metrics will return empty")


def setup_metrics(app: FastAPI, service_name: str) -> None:
    """
    Add Prometheus metrics to a FastAPI app.
    - GET /metrics endpoint
    - Request count, latency histograms, error rate
    """
    if not PROMETHEUS_AVAILABLE:
        @app.get("/metrics")
        async def metrics_stub() -> Response:
            return Response("# prometheus_client not installed\n", media_type="text/plain")
        return

    # ── Metrics definitions ───────────────────────────────────────────────────
    request_count = Counter(
        f"cloudvisor_{service_name}_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )
    request_latency = Histogram(
        f"cloudvisor_{service_name}_request_duration_seconds",
        "HTTP request latency",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    )
    active_requests = Gauge(
        f"cloudvisor_{service_name}_active_requests",
        "Currently active HTTP requests",
    )
    service_info = Info(
        f"cloudvisor_{service_name}_info",
        "Service information",
    )
    service_info.info({"service": service_name, "version": "1.0.0"})

    # ── Middleware ────────────────────────────────────────────────────────────
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Any) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        active_requests.inc()
        start = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration = time.time() - start
            endpoint = request.url.path
            method = request.method

            request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code),
            ).inc()
            request_latency.labels(method=method, endpoint=endpoint).observe(duration)
            active_requests.dec()

    # ── /metrics endpoint ─────────────────────────────────────────────────────
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        """Prometheus metrics endpoint — scraped by Prometheus every 15s."""
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
