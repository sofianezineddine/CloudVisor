"""
AI Router Service - Main FastAPI Application

Unified LLM gateway providing:
- Chat completions with multiple providers (OpenAI, OpenRouter, NVIDIA)
- Streaming responses
- Health monitoring
- Model management
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    logger.info(
        "ai_router_starting",
        environment=settings.app_environment,
        default_provider=settings.default_provider,
        available_providers=settings.get_available_providers(),
    )
    
    yield
    
    logger.info("ai_router_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="CloudVisor AI Router",
        description="Unified LLM gateway for OpenAI, OpenRouter, NVIDIA NIM, and other providers",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request
        logger.info(
            "request_processed",
            method=request.method,
            path=request.url.path,
            duration=process_time,
            status_code=response.status_code,
        )
        
        return response
    
    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    
    # Include API routes
    app.include_router(router, prefix="/v1")
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": "CloudVisor AI Router",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/v1/health",
        }
    
    return app


# Create the application instance
app = create_app()
