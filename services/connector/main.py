from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
import logging
import os

from cloudvisor_utils.config import get_settings

from app.core.dependencies import init_dependencies, shutdown_dependencies
from app.api.routes import accounts_router, onboarding_router, resources_router
from app.core.config import get_connector_settings

# ── Structured JSON logging (spec §2.1) ──────────────────────────────────────
def _configure_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging to stdout."""
    try:
        import structlog
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        # Also configure stdlib logging to route through structlog
        logging.basicConfig(
            format="%(message)s",
            level=getattr(logging, log_level.upper(), logging.INFO),
        )
    except ImportError:
        # structlog not installed — fall back to plain logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        )


logger = logging.getLogger("connector")


def create_app() -> FastAPI:
    settings = get_settings()
    connector_settings = get_connector_settings()

    log_level = getattr(settings.app, "log_level", "INFO") if hasattr(settings, "app") else os.getenv("APP_LOG_LEVEL", "INFO")
    _configure_logging(log_level)
    logger.info("Starting CloudVisor Connector service")

    app = FastAPI(
        title="CloudVisor Connector",
        description="Cloud asset ingestion and discovery service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Initializing dependencies")

        # ── OpenTelemetry tracing (spec §2.1) ─────────────────────────────────
        otel_enabled = getattr(getattr(settings, "otel", None), "enabled", False) or \
                       os.getenv("OTEL_ENABLED", "false").lower() == "true"
        if otel_enabled:
            try:
                from cloudvisor_utils.tracing import setup_tracing, instrument_fastapi
                otlp_endpoint = getattr(getattr(settings, "otel", None), "otlp_endpoint", None) or \
                                os.getenv("OTEL_OTLP_ENDPOINT", "http://localhost:4317")
                setup_tracing(
                    service_name="cloudvisor-connector",
                    otlp_endpoint=otlp_endpoint,
                    enabled=True,
                )
                instrument_fastapi(app)
                logger.info(f"OpenTelemetry tracing enabled → {otlp_endpoint}")
            except Exception as e:
                logger.warning(f"OpenTelemetry setup failed (non-fatal): {e}")

        await init_dependencies(settings)
        # Import after init to get initialized values
        from app.core.dependencies import _session_factory, _redis_client
        app.state.session_factory = _session_factory
        app.state.redis = _redis_client

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down dependencies")
        await shutdown_dependencies()

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "connector"}

    @app.get("/ready")
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "connector"}

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    app.include_router(accounts_router, prefix="/internal")
    app.include_router(onboarding_router, prefix="/internal")
    app.include_router(resources_router, prefix="/internal")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "connector.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.environment == "development",
    )
