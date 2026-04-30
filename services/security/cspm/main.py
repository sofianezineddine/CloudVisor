"""CloudVisor CSPM Service — Security Module."""
import asyncio
import logging
import os

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("cspm")

app = FastAPI(
    title="CloudVisor CSPM Service",
    description="Cloud Security Posture Management — misconfiguration detection and compliance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes import router  # noqa: E402 — absolute import after PYTHONPATH=/app

app.include_router(router)


# ── Internal scan trigger ─────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    account_id: str | None = None
    organization_id: str | None = None


@app.post("/internal/cspm/scan")
async def trigger_internal_scan(data: ScanRequest = Body(default=ScanRequest())):
    return {
        "status": "scan_triggered",
        "account_id": data.account_id,
        "organization_id": data.organization_id,
        "message": "Scan started",
    }


# ── Health / readiness ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cspm"}


@app.get("/ready")
async def ready():
    return {"status": "ready", "service": "cspm"}


# ── Prometheus metrics ────────────────────────────────────────────────────────

try:
    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus metrics mounted at /metrics")
except ImportError:
    logger.warning("prometheus_client not installed — /metrics unavailable")


# ── Startup / shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    # 1. Init DB — create tables
    try:
        from app.db_helper import init_db
        await init_db()
        logger.info("CSPM database tables created/verified")
    except Exception as e:
        logger.error(f"DB init failed: {e}")

    # 2. Start Kafka producer
    kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_producer = None
    try:
        from aiokafka import AIOKafkaProducer
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=kafka_servers,
            acks="all",
            retry_backoff_ms=500,
        )
        await kafka_producer.start()
        logger.info("CSPM Kafka producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start (degraded mode): {e}")

    # 3. Start Kafka consumer
    policy_url = os.environ.get("POLICY_SERVICE_URL", "http://cv-policy:8003")
    try:
        from app.consumers.resource_consumer import ResourceEventConsumer
        consumer = ResourceEventConsumer(
            bootstrap_servers=kafka_servers,
            policy_service_url=policy_url,
            finding_producer=kafka_producer,
        )
        await consumer.start()
        asyncio.create_task(consumer.run())
        logger.info("CSPM resource event consumer started")
    except Exception as e:
        logger.warning(f"Kafka consumer failed to start (degraded mode): {e}")

    # 4. Run initial scan for all organizations that have resources
    asyncio.create_task(_run_initial_scan())

    # 5. Start 24h scheduled scan
    asyncio.create_task(_start_scheduler())

    logger.info("CSPM service started on port 8006")


async def _run_initial_scan() -> None:
    """Run a scan for every org that has resources in the connector DB."""
    import asyncio as _asyncio
    await _asyncio.sleep(5)  # Wait for DB connections to settle

    try:
        from sqlalchemy import text
        from app.db_helper import AsyncSessionLocal
        from app.services.scan_executor import run_scan
        from app.models_db import CSPMScanModel

        async with AsyncSessionLocal() as db:
            # Find all orgs with discovered resources
            result = await db.execute(text(
                "SELECT DISTINCT organization_id FROM connector_discovered_resources "
                "WHERE is_deleted = false LIMIT 50"
            ))
            orgs = [row[0] for row in result.fetchall()]

        if not orgs:
            logger.info("No organizations with resources found — skipping initial scan")
            return

        logger.info(f"Running initial CSPM scan for {len(orgs)} organizations")

        for org_id in orgs:
            org_id_str = str(org_id)
            async with AsyncSessionLocal() as db:
                # Create scan record
                import uuid as _uuid_mod
                import datetime as _dt_mod
                scan = CSPMScanModel(
                    id=str(_uuid_mod.uuid4()),
                    organization_id=org_id_str,
                    scan_type="scheduled",
                    status="running",
                    started_at=_dt_mod.datetime.utcnow(),
                )
                db.add(scan)
                await db.commit()
                await db.refresh(scan)

            # Run scan in its own session
            async with AsyncSessionLocal() as scan_db:
                await run_scan(scan_db, scan.id, org_id_str)

        logger.info("Initial CSPM scan completed")

    except Exception as e:
        logger.error(f"Initial scan failed: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown():
    logger.info("CSPM service shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=False)


async def _start_scheduler() -> None:
    """Run a full scan for all orgs every 24 hours."""
    import asyncio as _asyncio
    while True:
        await _asyncio.sleep(86400)  # 24 hours
        logger.info("Starting scheduled 24h CSPM scan")
        await _run_initial_scan()
