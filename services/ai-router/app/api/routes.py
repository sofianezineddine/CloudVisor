"""
AI Router API Routes
"""
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.providers.base import ChatCompletionRequest, Message
from app.providers.manager import get_provider_manager

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatMessage(BaseModel):
    """Chat message for API requests."""
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request."""
    messages: list[ChatMessage] = Field(..., description="List of messages")
    model: Optional[str] = Field(None, description="Model to use (optional)")
    provider: Optional[str] = Field(None, description="Provider: openai, openrouter, nvidia")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Max tokens to generate")
    stream: bool = Field(False, description="Stream response")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)


class ChatResponse(BaseModel):
    """Chat completion response."""
    id: str
    provider: str
    model: str
    content: str
    usage: dict
    finish_reason: Optional[str]


class ProviderStatus(BaseModel):
    """Provider status information."""
    name: str
    available: bool
    healthy: bool
    models: list[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"
    providers: dict[str, bool]


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    manager = get_provider_manager()
    provider_health = await manager.health_check_all()
    
    return HealthResponse(
        status="healthy" if any(provider_health.values()) else "degraded",
        providers=provider_health,
    )


@router.get("/providers", response_model=list[ProviderStatus])
async def list_providers():
    """List all available LLM providers and their status."""
    manager = get_provider_manager()
    available = manager.list_available_providers()
    
    providers = []
    for name in available:
        try:
            provider = manager.get_provider(name)
            healthy = await provider.health_check()
            models = await provider.list_models()
            providers.append(ProviderStatus(
                name=name,
                available=True,
                healthy=healthy,
                models=models,
            ))
        except Exception as e:
            providers.append(ProviderStatus(
                name=name,
                available=False,
                healthy=False,
                models=[],
            ))
    
    return providers


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Create a chat completion.
    
    Unified endpoint that works with any configured provider.
    """
    manager = get_provider_manager()
    
    try:
        provider = manager.get_provider(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Convert request to provider format
    provider_request = ChatCompletionRequest(
        model=request.model or provider.default_model,
        messages=[Message(role=m.role, content=m.content) for m in request.messages],
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=False,
        top_p=request.top_p,
        presence_penalty=request.presence_penalty,
        frequency_penalty=request.frequency_penalty,
    )
    
    try:
        response = await provider.chat_completion(provider_request)
        return ChatResponse(
            id=response.id,
            provider=provider.name,
            model=response.model,
            content=response.content,
            usage=response.usage,
            finish_reason=response.finish_reason,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Provider error: {str(e)}")


@router.post("/chat/completions/stream")
async def chat_completion_stream(request: ChatRequest):
    """
    Stream a chat completion.
    
    Returns Server-Sent Events (SSE) with chunked response.
    """
    manager = get_provider_manager()
    
    try:
        provider = manager.get_provider(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    provider_request = ChatCompletionRequest(
        model=request.model or provider.default_model,
        messages=[Message(role=m.role, content=m.content) for m in request.messages],
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=True,
        top_p=request.top_p,
    )
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in provider.chat_completion_stream(provider_request):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/models")
async def list_models(provider: Optional[str] = None):
    """List available models for a provider."""
    manager = get_provider_manager()
    
    if provider:
        try:
            p = manager.get_provider(provider)
            models = await p.list_models()
            return {"provider": provider, "models": models}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Return models for all providers
    all_models = {}
    for name in manager.list_available_providers():
        try:
            p = manager.get_provider(name)
            all_models[name] = await p.list_models()
        except Exception:
            all_models[name] = []
    
    return all_models
