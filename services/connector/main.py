"""CloudVisor Connector entry point — FastAPI app with lifespan management."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from cloudvisor_utils.config import get_settings

from app.core.dependencies import init_dependencies, shutdown_dependencies
from app.api.routes import accounts_router, onboarding_router, resources_router
from app.core.config import get_connector_settings


# ── Structured JSON logging ──────────────────────────────────────────────────
def _configure_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging to stdout.

    Routes every stdlib ``logging`` call through structlog so all logs —
    including those from third-party libs — come out as single-line JSON with
    ``service_name``, ``correlation_id``, ``organization_id`` merged in from
    structlog's contextvars (set by ``RequestContextMiddleware`` below).
    """
    try:
        import structlog
        from structlog.stdlib import ProcessorFormatter

        shared_processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        structlog.configure(
            processors=[
                *shared_processors,
                ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        formatter = ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
        root_handler = logging.StreamHandler()
        root_handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        # Replace any existing handlers so logs don't double-print
        root_logger.handlers = [root_handler]
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    except ImportError:
        # structlog not installed — fall back to plain logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format='{"time":"%(asctime)s","level":"%(levelname)s",'
                   '"logger":"%(name)s","message":"%(message)s"}',
        )


logger = logging.getLogger("connector")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Inject correlation_id and org_id into structlog contextvars per request.

    Every log line emitted during request handling will include these fields
    without each call site having to pass them explicitly — as required by
    spec §2.1 observability.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            import structlog
            # Correlation ID: prefer the one the client sent, else generate
            import uuid
            correlation_id = (
                request.headers.get("X-Correlation-ID")
                or request.headers.get("X-Request-ID")
                or str(uuid.uuid4())
            )
            # Org ID: set by the gateway, or decoded from the Bearer token below
            org_id = request.headers.get("X-Org-ID", "")
            if not org_id:
                try:
                    from app.core.auth import get_org_id_from_token
                    org_id = get_org_id_from_token(
                        request.headers.get("Authorization", "")
                    ) or ""
                except Exception:
                    org_id = ""

            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                service_name="cloudvisor-connector",
                correlation_id=correlation_id,
                organization_id=org_id or "anonymous",
                http_method=request.method,
                http_path=request.url.path,
            )
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        except ImportError:
            return await call_next(request)
        finally:
            try:
                import structlog
                structlog.contextvars.clear_contextvars()
            except ImportError:
                pass


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared resources on startup and clean them up on shutdown."""
    settings = get_settings()
    connector_settings = get_connector_settings()

    log_level = getattr(settings.app, "log_level", "INFO") if hasattr(settings, "app") \
        else os.getenv("APP_LOG_LEVEL", "INFO")
    _configure_logging(log_level)
    logger.info("Starting CloudVisor Connector service")

    # Warn if envelope encryption is unconfigured (spec §8)
    if not os.getenv("CONNECTOR_CREDENTIAL_MASTER_KEY", "").strip():
        logger.warning(
            "CONNECTOR_CREDENTIAL_MASTER_KEY is not set — customer cloud "
            "credentials will be stored plaintext. Configure it for production."
        )

    # ── OpenTelemetry tracing ─────────────────────────────────────────────────
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
    from app.core.dependencies import _session_factory, _redis_client, _engine
    app.state.session_factory = _session_factory
    app.state.redis = _redis_client
    app.state.engine = _engine

    # ── OTel SQLAlchemy instrumentation (after engine is created) ─────────────
    if otel_enabled and _engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument(
                engine=_engine.sync_engine if hasattr(_engine, "sync_engine") else _engine
            )
            logger.info("OpenTelemetry SQLAlchemy instrumentation enabled")
        except Exception as e:
            logger.debug(f"SQLAlchemy OTel instrumentation skipped: {e}")

    try:
        yield
    finally:
        logger.info("Shutting down dependencies")
        await shutdown_dependencies()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudVisor Connector",
        description="Cloud asset ingestion and discovery service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS (no wildcard when credentials are allowed — browsers reject it) ──
    # Explicit origins can be overridden via CONNECTOR_CORS_ORIGINS (comma list).
    cors_env = os.getenv("CONNECTOR_CORS_ORIGINS", "").strip()
    if cors_env:
        allow_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
    else:
        allow_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    @app.get("/health", tags=["monitoring"])
    async def health_check() -> dict:
        return {"status": "healthy", "service": "connector"}

    @app.get("/ready", tags=["monitoring"])
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "connector"}

    @app.get("/metrics", tags=["monitoring"])
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    app.include_router(accounts_router, prefix="/internal")
    app.include_router(onboarding_router, prefix="/internal")
    app.include_router(resources_router, prefix="/internal")

    # Circuit-breaker admin endpoints (see app/api/routes/admin.py)
    try:
        from app.api.routes.admin import router as admin_router
        app.include_router(admin_router, prefix="/internal")
    except ImportError:
        pass

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.environment == "development",
    )
