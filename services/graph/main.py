"""CloudVisor Graph Service — Unified Asset Graph & Inventory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from cloudvisor_utils.config import get_settings
from cloudvisor_utils.logging_utils import configure_logging, get_logger

from app.core.dependencies import (
    init_dependencies,
    shutdown_dependencies,
    get_graph_settings_cached,
    _neo4j_client,
    _elasticsearch_client,
    _redis_client,
    _session_factory,
)
from app.core.config import get_graph_settings
from app.api.routes import assets_router


def _setup_tracing(service_name: str, otlp_endpoint: str | None = None) -> None:
    """Configure OpenTelemetry tracing — Rule 9: observability is not optional."""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)


def create_app() -> FastAPI:
    settings = get_settings()
    graph_settings = get_graph_settings()

    configure_logging(
        service_name=graph_settings.service_name,
        log_level=settings.app.log_level,
    )

    logger = get_logger("graph")
    logger.info("Starting CloudVisor Graph service")

    # ── OpenTelemetry tracing ─────────────────────────────────────────────────
    otlp_endpoint = getattr(settings, "otlp_endpoint", None) or getattr(
        graph_settings, "otlp_endpoint", None
    )
    _setup_tracing(
        service_name=graph_settings.service_name,
        otlp_endpoint=otlp_endpoint,
    )

    app = FastAPI(
        title="CloudVisor Graph",
        description="Unified Asset Graph & Inventory Service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Instrument FastAPI with OTel (auto-traces every request)
    FastAPIInstrumentor.instrument_app(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Prometheus metrics — Rule 9: observability is not optional
    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "graph")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Initializing Graph service dependencies")
        await init_dependencies(settings, graph_settings)

        # Wire app.state so route dependencies can access clients
        import app.core.dependencies as deps
        app.state.neo4j = deps._neo4j_client
        app.state.elasticsearch = deps._elasticsearch_client
        app.state.redis = deps._redis_client
        app.state.session_factory = deps._session_factory
        app.state.graph_settings = graph_settings
        if app.state.neo4j:
            try:
                await app.state.neo4j.create_constraints()
                logger.info("Neo4j constraints created")
            except Exception as e:
                logger.warning(f"Neo4j constraints: {e}")

        if app.state.elasticsearch:
            try:
                from app.clients.elasticsearch import ASSET_MAPPINGS
                await app.state.elasticsearch.create_index("assets", ASSET_MAPPINGS)
                logger.info("Elasticsearch index ready")
            except Exception as e:
                logger.warning(f"Elasticsearch index: {e}")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down Graph service")
        await shutdown_dependencies()

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "graph"}

    @app.get("/ready")
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "graph"}

    app.include_router(assets_router, prefix="/internal")

    # ── GraphQL endpoint (spec §3.2) ──────────────────────────────────────────
    try:
        from strawberry.fastapi import GraphQLRouter
        from app.api.graphql_schema import schema

        async def get_graphql_context():
            """Provide Neo4j and Redis clients to GraphQL resolvers."""
            import app.core.dependencies as deps
            return {
                "neo4j": deps._neo4j_client,
                "redis": deps._redis_client,
            }

        graphql_app = GraphQLRouter(schema, context_getter=get_graphql_context)
        app.include_router(graphql_app, prefix="/graphql")
        logger.info("GraphQL endpoint mounted at /graphql")
    except ImportError as e:
        logger.warning(f"GraphQL not available (strawberry not installed): {e}")
    except Exception as e:
        logger.warning(f"GraphQL setup failed: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "graph.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.app.environment == "development",
    )
