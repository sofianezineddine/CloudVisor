"""
CloudVisor Q (Copilot) proxy routes — forwards all copilot requests to the Copilot service.

POST   /v1/copilot/query
GET    /v1/copilot/history
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_copilot_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotQueryRequest(BaseModel):
    query: str
    context: dict[str, Any] | None = None
    stream: bool = False


@router.post("/query", response_model=None)
async def query_copilot(
    data: CopilotQueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    request: Request = None,
):
    """
    Query CloudVisor Q with a natural language question.
    
    Supports both streaming and non-streaming responses.
    """
    t0 = time.monotonic()
    copilot = get_copilot_proxy()
    
    # Prepare headers for copilot service
    auth_token = request.headers.get("authorization") if request else None
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": user.organization_id,
    }
    if auth_token:
        headers["Authorization"] = auth_token
    
    try:
        # Add organization_id and user_id to the request
        payload = data.model_dump()
        payload["organization_id"] = user.organization_id
        payload["user_id"] = user.user_id
        
        if data.stream:
            # For streaming responses, we need to proxy the SSE stream
            import httpx
            import os
            
            copilot_url = os.environ.get("API_COPILOT_SERVICE_URL", "http://cv-copilot:8010")
            
            async def stream_generator():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{copilot_url}/v1/copilot/query",
                        json=payload,
                        headers=headers,
                    ) as response:
                        async for chunk in response.aiter_text():
                            yield chunk
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            result = await copilot.post(
                "/v1/copilot/query",
                json=payload,
                headers=headers,
            )
            return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
            
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Copilot service unavailable: {e}")


@router.get("/history")
async def get_query_history(
    limit: int = 10,
    user: AuthenticatedUser = Depends(get_current_user),
    request: Request = None,
) -> dict[str, Any]:
    """
    Get the user's recent query history.
    """
    t0 = time.monotonic()
    copilot = get_copilot_proxy()
    
    # Prepare headers for copilot service
    auth_token = request.headers.get("authorization") if request else None
    headers = {
        "X-Org-ID": user.organization_id,
    }
    if auth_token:
        headers["Authorization"] = auth_token
    
    try:
        result = await copilot.get(
            "/v1/copilot/history",
            params={
                "organization_id": user.organization_id,
                "user_id": user.user_id,
                "limit": limit,
            },
            headers=headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Copilot service unavailable: {e}")
