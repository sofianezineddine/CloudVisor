"""CloudVisor Q (Copilot) Service - RAG-powered Security Intelligence Assistant."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from fastapi.responses import Response
import logging

from cloudvisor_utils.config import get_settings
from cloudvisor_utils.logging_utils import configure_logging, get_logger
from cloudvisor_utils.tracing import setup_tracing, instrument_fastapi

from app.core.dependencies import init_dependencies, shutdown_dependencies
from app.core.config import get_copilot_settings
from app.api import query_router, sessions_router

logger = logging.getLogger("copilot")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    copilot_settings = get_copilot_settings()

    configure_logging(
        service_name=copilot_settings.service_name,
        log_level=settings.app.log_level,
    )

    logger = get_logger("copilot")
    logger.info("Starting CloudVisor Q (Copilot) service")

    app = FastAPI(
        title="CloudVisor Q",
        description="RAG-powered Security Intelligence Assistant",
        version="1.0.0",
        docs_url="/v1/docs",
        redoc_url="/v1/redoc",
    )

    # CORS middleware
    cors_origins = getattr(copilot_settings, "cors_origins", "http://localhost:3000")
    origins_list = [o.strip() for o in cors_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list + [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # OpenTelemetry tracing
    if settings.otel.enabled:
        setup_tracing(
            service_name=f"cloudvisor-{copilot_settings.service_name}",
            otlp_endpoint=settings.otel.otlp_endpoint,
            enabled=settings.otel.enabled,
        )
        instrument_fastapi(app)

    # Metrics
    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "copilot")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize dependencies on startup."""
        logger.info("Initializing dependencies")
        await init_dependencies(settings, copilot_settings)
        from app.core import dependencies as deps
        app.state.session_factory = deps._session_factory
        app.state.redis = deps._redis_client
        app.state.kafka_producer = deps._kafka_producer

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Clean up dependencies on shutdown."""
        logger.info("Shutting down dependencies")
        await shutdown_dependencies()

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "service": "copilot"}

    @app.get("/ready")
    async def readiness_check() -> dict:
        """Readiness check endpoint."""
        return {"status": "ready", "service": "copilot"}

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Include routers
    app.include_router(query_router, prefix="/v1")
    app.include_router(sessions_router, prefix="/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "services.copilot.main:app",
        host="0.0.0.0",
        port=8010,
        reload=settings.app.environment == "development",
    )
