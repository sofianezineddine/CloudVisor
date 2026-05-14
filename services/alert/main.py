"""CloudVisor Alert Service — Alert Pipeline & Notification Engine."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloudvisor_utils.config import get_settings
from cloudvisor_utils.logging_utils import configure_logging, get_logger

from app.core.dependencies import (
    init_dependencies,
    shutdown_dependencies,
    get_alert_settings_cached,
)
from app.core.config import get_alert_settings
from app.api.routes import findings_router, suppressions_router, notifications_router, notifications_test_router, incidents_router, webhooks_router


def create_app() -> FastAPI:
    settings = get_settings()
    alert_settings = get_alert_settings()

    configure_logging(
        service_name=alert_settings.service_name,
        log_level=settings.app.log_level,
    )

    logger = get_logger("alert")
    logger.info("Starting CloudVisor Alert service")

    app = FastAPI(
        title="CloudVisor Alert",
        description="Alert Pipeline & Notification Engine",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:8005",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Prometheus metrics (Rule 9: every service exposes /metrics) ───────────
    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "alert")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")

    # ── OpenTelemetry tracing (Rule 9: OTel traces from first commit) ─────────
    try:
        from cloudvisor_utils.tracing import setup_tracing, instrument_fastapi
        setup_tracing(service_name=alert_settings.service_name)
        instrument_fastapi(app)
        logger.info("OpenTelemetry tracing initialized")
    except Exception as e:
        logger.warning(f"OTel tracing setup failed (non-fatal): {e}")

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Initializing Alert service dependencies")
        await init_dependencies(settings, alert_settings)

        import app.core.dependencies as deps
        app.state.session_factory = deps._session_factory
        app.state.redis = deps._redis_client

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down Alert service")
        await shutdown_dependencies()

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "alert"}

    @app.get("/ready")
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "alert"}

    app.include_router(findings_router, prefix="/internal")
    app.include_router(suppressions_router, prefix="/internal")
    app.include_router(notifications_router, prefix="/internal")
    app.include_router(notifications_test_router, prefix="/internal")
    app.include_router(incidents_router, prefix="/internal")
    app.include_router(webhooks_router, prefix="/internal")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "alert.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.app.environment == "development",
    )
