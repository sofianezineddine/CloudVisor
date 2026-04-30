# CloudVisor Service Implementation Pattern

## Overview
Based on analysis of existing services (auth, connector), here's the standard pattern for implementing a new CloudVisor service.

## Directory Structure

```
services/<service-name>/
├── main.py                   # Entry point - FastAPI app creation
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Python project config (optional)
├── README.md                # Service documentation
├── __init__.py              # Package marker
├── app/
│   ├── api/                 # FastAPI routers
│   │   ├── __init__.py
│   │   └── routes/          # Route modules
│   │       ├── __init__.py
│   │       └── <resource>.py
│   ├── core/                # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py        # Service-specific settings
│   │   ├── dependencies.py  # Dependency injection
│   │   └── database.py      # DB setup (if needed)
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── <model>.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   └── <schema>.py
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   └── <service>.py
│   ├── repositories/        # Data access layer (optional)
│   │   ├── __init__.py
│   │   └── <repository>.py
│   ├── producers/           # Kafka producers (if needed)
│   │   ├── __init__.py
│   │   └── <producer>.py
│   └── consumers/           # Kafka consumers (if needed)
│       ├── __init__.py
│       └── <consumer>.py
└── tests/
    ├── __init__.py
    ├── conftest.py          # Pytest fixtures
    ├── unit/                # Unit tests
    │   └── test_<module>.py
    └── integration/         # Integration tests
        └── test_<module>.py
```

## Key Files & Patterns

### 1. main.py (Entry Point)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from cloudvisor_utils.config import get_settings
from cloudvisor_utils.logging_utils import configure_logging, get_logger
from cloudvisor_utils.tracing import setup_tracing, instrument_fastapi

from app.core.dependencies import init_dependencies, shutdown_dependencies
from app.core.config import get_<service>_settings
from app.api.routes import <router1>, <router2>

def create_app() -> FastAPI:
    settings = get_settings()
    service_settings = get_<service>_settings()
    
    configure_logging(
        service_name=service_settings.service_name,
        log_level=settings.app.log_level,
    )
    
    logger = get_logger("<service>")
    logger.info("Starting CloudVisor <Service> service")
    
    app = FastAPI(
        title="CloudVisor <Service>",
        description="<Service description>",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # OpenTelemetry tracing (optional)
    if settings.otel.enabled:
        setup_tracing(
            service_name=f"cloudvisor-{service_settings.service_name}",
            otlp_endpoint=settings.otel.otlp_endpoint,
            enabled=settings.otel.enabled,
        )
        instrument_fastapi(app)
    
    # Metrics (optional)
    try:
        from cloudvisor_utils.metrics import setup_metrics
        setup_metrics(app, "<service>")
    except Exception as e:
        logger.warning(f"Metrics setup failed: {e}")
    
    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Initializing dependencies")
        await init_dependencies(settings, service_settings)
        app.state.session_factory = deps._session_factory
        app.state.redis = deps._redis_client
    
    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Shutting down dependencies")
        await shutdown_dependencies()
    
    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "<service>"}
    
    @app.get("/ready")
    async def readiness_check() -> dict:
        return {"status": "ready", "service": "<service>"}
    
    # Include routers
    app.include_router(<router1>)
    app.include_router(<router2>)
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "services.<service>.main:app",
        host="0.0.0.0",
        port=<PORT>,
        reload=settings.app.environment == "development",
    )
```

### 2. app/core/config.py (Service-Specific Settings)

```python
"""Pydantic settings specific to the <Service> service."""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find the .env file in the project root
_env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"

class <Service>Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="<SERVICE>_",
        env_file=_env_path if _env_path.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    service_name: str = Field(default="<service>")
    # Add service-specific settings here
    
def get_<service>_settings() -> <Service>Settings:
    return <Service>Settings()
```

### 3. app/core/dependencies.py (Dependency Injection)

```python
"""FastAPI dependency injection for the <service> service."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings, get_settings
from cloudvisor_utils.tracing import get_tracer

from .config import <Service>Settings, get_<service>_settings
from .database import create_engine, create_session, create_db_session

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_engine: object | None = None
_session_factory: object | None = None
_kafka_producer: object | None = None

async def init_dependencies(settings: CloudvisorSettings, service_settings: <Service>Settings) -> None:
    """Initialize shared dependencies."""
    global _redis_client, _engine, _session_factory, _kafka_producer
    
    # Initialize database
    _engine = create_engine(settings.db.url)
    _session_factory = create_session(_engine)
    
    # Create tables
    from ..models import Base
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Redis
    _redis_client = redis.from_url(
        settings.redis.url,
        password=settings.redis.password,
        db=settings.redis.db,
        decode_responses=True,
    )
    
    # Initialize Kafka producer (if needed)
    try:
        kafka_servers = settings.kafka.bootstrap_servers
        from ..producers.<producer> import <Producer>
        _kafka_producer = <Producer>(bootstrap_servers=kafka_servers)
        await _kafka_producer.start()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start: {e}")
        _kafka_producer = None
    
    logger.info("<Service> dependencies initialized")

async def shutdown_dependencies() -> None:
    """Clean up dependencies."""
    global _redis_client, _engine, _kafka_producer
    
    if _kafka_producer:
        await _kafka_producer.stop()
        _kafka_producer = None
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _engine:
        from .database import dispose_engine
        await dispose_engine(_engine)
        _engine = None

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS."""
    org_id = request.headers.get("X-Org-ID")
    session_factory = getattr(request.app.state, "session_factory", None) or _session_factory
    if session_factory is None:
        raise RuntimeError("Database session factory is not initialized")
    async with create_db_session(session_factory, org_id) as session:
        yield session

async def get_redis(request: Request) -> AsyncGenerator[redis.Redis, None]:
    """Dependency for Redis client."""
    client = getattr(request.app.state, "redis", None) or _redis_client
    if client is None:
        raise RuntimeError("Redis client is not initialized")
    yield client

@lru_cache
def get_<service>_settings_cached() -> <Service>Settings:
    return get_<service>_settings()
```

### 4. app/models/<model>.py (SQLAlchemy Models)

```python
"""SQLAlchemy ORM models for <Service> service."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class <Model>Model(Base):
    """<Model> model."""
    
    __tablename__ = "<table_name>"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    # Add fields here
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

### 5. app/schemas/<schema>.py (Pydantic Schemas)

```python
"""Pydantic schemas for <Service> service."""

from datetime import datetime
from pydantic import BaseModel, Field

class <Resource>Request(BaseModel):
    """<Resource> request."""
    # Request fields

class <Resource>Response(BaseModel):
    """<Resource> response."""
    id: str
    # Response fields
    created_at: datetime
```

### 6. app/api/routes/<resource>.py (API Routes)

```python
"""API routes for <resource>."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db, get_redis
from ...schemas import <Resource>Request, <Resource>Response
from ...services import <Resource>Service

router = APIRouter(prefix="/<resource>", tags=["<resource>"])

@router.post("/", response_model=<Resource>Response, status_code=status.HTTP_201_CREATED)
async def create_<resource>(
    data: <Resource>Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> <Resource>Response:
    """Create a new <resource>."""
    service = <Resource>Service(db, redis)
    try:
        result = await service.create(data)
        return <Resource>Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{id}", response_model=<Resource>Response)
async def get_<resource>(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> <Resource>Response:
    """Get <resource> by ID."""
    service = <Resource>Service(db)
    result = await service.get_by_id(id)
    if not result:
        raise HTTPException(status_code=404, detail="<Resource> not found")
    return <Resource>Response(**result)
```

### 7. app/services/<service>.py (Business Logic)

```python
"""Business logic for <resource>."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import <Model>Model

class <Resource>Service:
    """Service for <resource> operations."""
    
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
    
    async def create(self, data: dict) -> dict:
        """Create a new <resource>."""
        # Business logic here
        pass
    
    async def get_by_id(self, id: str) -> dict | None:
        """Get <resource> by ID."""
        result = await self.db.execute(
            select(<Model>Model).where(<Model>Model.id == id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return {
            "id": model.id,
            # Map fields
        }
```

### 8. Dockerfile

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install shared utils package
COPY packages/utils /app/packages/utils
RUN pip install --no-cache-dir /app/packages/utils

# Install service dependencies
COPY services/<service>/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service source
COPY services/<service> /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:<PORT>/health')" || exit 1

EXPOSE <PORT>

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "<PORT>"]
```

### 9. requirements.txt

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.25
asyncpg>=0.29.0
redis>=5.0.0
aiokafka>=0.10.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
structlog>=24.1.0
opentelemetry-api>=1.22.0
opentelemetry-sdk>=1.22.0
httpx>=0.26.0
```

## Key Principles

1. **Shared Utilities**: Use `cloudvisor_utils` package for common functionality (config, logging, tracing, metrics)
2. **Multi-Tenancy**: Always include `organization_id` in models and use RLS
3. **Dependency Injection**: Use FastAPI's dependency injection for DB, Redis, Kafka
4. **Separation of Concerns**: 
   - Routes handle HTTP
   - Services handle business logic
   - Models handle data structure
   - Repositories handle data access (optional)
5. **Error Handling**: Raise `ValueError` in services, convert to `HTTPException` in routes
6. **Observability**: Include health checks, metrics, and tracing from day one
7. **Testing**: Write both unit and integration tests

## Port Assignments

- 8000: Connector
- 8001: Graph
- 8002: Auth
- 8003: Policy
- 8004: Alert
- 8005: API Gateway
- 8006+: Module services (CSPM, CWPP, etc.)

## Environment Variables Pattern

All services use:
- `DB_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka brokers
- `OTEL_ENABLED`: Enable tracing
- `APP_LOG_LEVEL`: Logging level
- `<SERVICE>_*`: Service-specific settings

## Next Steps

When implementing a new service:
1. Copy the structure from an existing service (auth or connector)
2. Update service name, port, and specific settings
3. Define models based on the service's data needs
4. Implement business logic in services
5. Create API routes
6. Add Kafka producers/consumers if needed
7. Write tests
8. Update docker-compose.yml
9. Document in README.md
