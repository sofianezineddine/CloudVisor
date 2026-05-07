"""
CloudVisor Public API Service — Service 6 of the Foundation.

Base URL: http://localhost:8005/v1
Auth:     Authorization: Bearer <JWT>  OR  X-API-Key: cv_live_<key>

All responses use the standard envelope:
  { "data": ..., "meta": { "request_id", "total", "took_ms" }, "errors": [] }

Rate-limit headers on every response:
  X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
"""

import logging
import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import v1_router, graphql_standalone_router
from app.core.config import get_api_settings
from app.schemas.envelope import APIError, APIResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("api")

settings = get_api_settings()

# ── In-process rate-limit state (per org, per minute window) ─────────────────
# For production use Redis; this is a lightweight in-process fallback.
_rate_counters: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
_RATE_LIMIT = settings.rate_limit_requests_per_minute
_WINDOW = 60.0  # seconds


def _check_rate_limit(key: str) -> tuple[int, int, float]:
    """
    Returns (limit, remaining, reset_ts).
    Increments the counter for `key` within the current 1-minute window.
    """
    now = time.time()
    count, window_start = _rate_counters[key]
    if now - window_start >= _WINDOW:
        # New window
        count = 0
        window_start = now
    count += 1
    _rate_counters[key] = (count, window_start)
    remaining = max(0, _RATE_LIMIT - count)
    reset_ts = window_start + _WINDOW
    return _RATE_LIMIT, remaining, reset_ts


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudVisor Public API",
        description=(
            "Unified REST API for the CloudVisor CNAPP platform.\n\n"
            "**Auth:** `Authorization: Bearer <JWT>` or `X-API-Key: cv_live_<key>`\n\n"
            "**Base URL:** `https://api.cloudvisor.io/v1`"
        ),
        version="1.0.0",
        docs_url="/v1/docs",
        redoc_url="/v1/redoc",
        openapi_url="/v1/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID + timing + rate-limit headers middleware ───────────────────
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> Response:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        request.state.start_time = time.monotonic()

        # Derive a rate-limit key: prefer org from JWT/API-key, fall back to IP
        rate_key = request.client.host if request.client else "unknown"
        x_api_key = request.headers.get("x-api-key", "")
        auth_header = request.headers.get("authorization", "")
        if x_api_key:
            rate_key = f"apikey:{x_api_key[:20]}"
        elif auth_header.startswith("Bearer "):
            # Use first 20 chars of token as key (fast, no decode needed)
            rate_key = f"jwt:{auth_header[7:27]}"

        limit, remaining, reset_ts = _check_rate_limit(rate_key)

        if remaining == 0:
            return JSONResponse(
                status_code=429,
                content=APIResponse(
                    data=None,
                    errors=[
                        APIError(
                            code="RATE_LIMIT_EXCEEDED",
                            message="Rate limit exceeded. Please retry after the reset time.",
                        )
                    ],
                ).model_dump(),
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_ts)),
                    "Retry-After": str(int(reset_ts - time.time())),
                    "X-Request-ID": request_id,
                },
            )

        response = await call_next(request)

        # Attach standard headers to every response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Took-Ms"] = str(
            int((time.monotonic() - request.state.start_time) * 1000)
        )
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_ts))
        return response

    # ── Global exception handler — always return envelope format ──────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                data=None,
                errors=[APIError(code="INTERNAL_ERROR", message="An unexpected error occurred")],
            ).model_dump(),
        )

    # ── Prometheus metrics ────────────────────────────────────────────────────
    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "api")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")

        @app.get("/metrics", include_in_schema=False)
        async def metrics_stub() -> Response:
            return Response("# metrics unavailable\n", media_type="text/plain")

    # ── OpenTelemetry tracing (Rule 9: OTel traces from first commit) ─────────
    try:
        from cloudvisor_utils.tracing import setup_tracing, instrument_fastapi
        import os as _os
        otlp_endpoint = _os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        setup_tracing(service_name="api", otlp_endpoint=otlp_endpoint)
        instrument_fastapi(app)
        logger.info("OpenTelemetry tracing initialized")
    except Exception as e:
        logger.warning(f"OTel tracing setup failed (non-fatal): {e}")

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(v1_router)

    # ── GraphQL (POST /graphql — no /v1 prefix, standard convention) ──────────
    app.include_router(graphql_standalone_router)

    # ── WebSocket ─────────────────────────────────────────────────────────────
    from app.api.ws import ws_router
    app.include_router(ws_router)

    # ── Health / ready ────────────────────────────────────────────────────────
    @app.get("/health", include_in_schema=False)
    async def health() -> dict:
        return {"status": "healthy", "service": "api"}

    @app.get("/ready", include_in_schema=False)
    async def ready() -> dict:
        return {"status": "ready", "service": "api"}

    logger.info("CloudVisor Public API service started — /v1/docs for OpenAPI spec")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=False)
