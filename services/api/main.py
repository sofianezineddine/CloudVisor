"""
CloudVisor Public API Service — Service 6 of the Foundation.

Base URL: http://localhost:8005/v1
Auth:     Authorization: Bearer <JWT>

All responses use the standard envelope:
  { "data": ..., "meta": { "request_id", "total", "took_ms" }, "errors": [] }
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import v1_router
from app.core.config import get_api_settings
from app.schemas.envelope import APIError, APIResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("api")

settings = get_api_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudVisor Public API",
        description=(
            "Unified REST API for the CloudVisor CNAPP platform. "
            "All endpoints require Bearer JWT authentication."
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

    # ── Request ID + timing middleware ────────────────────────────────────────
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> Response:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        request.state.start_time = time.monotonic()

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Took-Ms"] = str(
            int((time.monotonic() - request.state.start_time) * 1000)
        )
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

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(v1_router)

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
