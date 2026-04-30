from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from cloudvisor_utils.config import get_settings
from cloudvisor_utils.logging_utils import configure_logging, get_logger
from cloudvisor_utils.tracing import setup_tracing, instrument_fastapi

from app.core.dependencies import (
    init_dependencies,
    shutdown_dependencies,
    get_auth_settings_cached,
)
from app.core.config import get_auth_settings
from app.api.routes import auth_router, mfa_router, sessions_router, internal_router, admin_router
from app.api.routes.sso import router as sso_router
from app.core import dependencies as deps


def create_app() -> FastAPI:
    settings = get_settings()
    auth_settings = get_auth_settings()

    configure_logging(
        service_name=auth_settings.service_name,
        log_level=settings.app.log_level,
    )

    logger = get_logger("auth")
    try:
        logger.info("Starting CloudVisor Auth service")
    except Exception:
        logging.getLogger("auth").info("Starting CloudVisor Auth service")

    app = FastAPI(
        title="CloudVisor Auth",
        description="Multi-Tenant Auth & RBAC Service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Parse CORS origins - allow localhost:3000 by default
    cors_origins = getattr(auth_settings, "cors_origins", "http://localhost:3000")
    origins_list = [o.strip() for o in cors_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list + [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:8002",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    if settings.otel.enabled:
        setup_tracing(
            service_name=f"cloudvisor-{auth_settings.service_name}",
            otlp_endpoint=settings.otel.otlp_endpoint,
            enabled=settings.otel.enabled,
        )
        instrument_fastapi(app)

    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "auth")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")

    @app.on_event("startup")
    async def startup_event() -> None:
        try:
            logger.info("Initializing dependencies")
        except Exception:
            logging.getLogger("auth").info("Initializing dependencies")
        await init_dependencies(settings, auth_settings)
        app.state.session_factory = deps._session_factory
        app.state.redis = deps._redis_client

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        try:
            logger.info("Shutting down dependencies")
        except Exception:
            logging.getLogger("auth").info("Shutting down dependencies")
        await shutdown_dependencies()

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "auth"}

    @app.get("/ready")
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "auth"}

    app.include_router(auth_router)
    app.include_router(mfa_router)
    app.include_router(sessions_router)
    app.include_router(internal_router)
    app.include_router(admin_router)
    app.include_router(sso_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "services.auth.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.app.environment == "development",
    )
