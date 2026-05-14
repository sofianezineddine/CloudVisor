"""CloudVisor Policy Service — OPA/Rego Policy Engine."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloudvisor_utils.config import get_settings
from cloudvisor_utils.logging_utils import configure_logging, get_logger

from app.core.dependencies import (
    init_dependencies,
    shutdown_dependencies,
    get_policy_settings_cached,
)
from app.core.config import get_policy_settings
from app.api import policy_router, compliance_router, internal_router


def create_app() -> FastAPI:
    settings = get_settings()
    policy_settings = get_policy_settings()

    configure_logging(
        service_name=policy_settings.service_name,
        log_level=settings.app.log_level,
    )

    logger = get_logger("policy")
    logger.info("Starting CloudVisor Policy service")

    app = FastAPI(
        title="CloudVisor Policy",
        description="Policy Engine — OPA/Rego Rules Evaluation",
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

    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "policy")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Initializing Policy service dependencies")
        await init_dependencies(settings, policy_settings)

        import app.core.dependencies as deps
        app.state.session_factory = deps._session_factory
        app.state.redis = deps._redis_client
        app.state.opa = deps._opa_service

        # Load CSPM rules into OPA
        logger.info("Loading CSPM rules into OPA")
        try:
            from app.services.rule_loader import RuleLoaderService
            rule_loader = RuleLoaderService(deps._opa_service)
            results = await rule_loader.load_all_rules()
            logger.info(f"CSPM rules loaded: {results['loaded']} successful, {results['failed']} failed")
            if results['errors']:
                for error in results['errors']:
                    logger.warning(f"Rule loading error: {error}")
        except Exception as e:
            logger.error(f"Failed to load CSPM rules: {e}")
            # Don't fail startup if rule loading fails

        # Seed built-in rules into policy DB (handled by init_dependencies)
        logger.info("Rule seeding handled by init_dependencies")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down Policy service")
        await shutdown_dependencies()

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "policy"}

    @app.get("/ready")
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "policy"}

    app.include_router(policy_router)
    app.include_router(compliance_router)
    app.include_router(internal_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "policy.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.app.environment == "development",
    )
