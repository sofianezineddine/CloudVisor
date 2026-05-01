"""API routes for copilot queries."""

import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_db, get_redis, get_copilot_settings_cached
from ..schemas import CopilotQueryRequest, CopilotQueryResponse
from ..services import RAGPipeline
from ..repositories.query_log_repo import QueryLogRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["copilot"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


@router.post(
    "/query",
    response_model=CopilotQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query CloudVisor Q",
    description="Ask a natural language question about your cloud security posture",
)
async def query_copilot(
    query_request: CopilotQueryRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> CopilotQueryResponse | StreamingResponse:
    """
    Query CloudVisor Q with a natural language question.

    Implements the full 6-step RAG pipeline:
    1. Intent classification
    2. Query embedding (stub — pending vector store)
    3. Multi-source context retrieval (concurrent)
    4. Prompt construction
    5. LLM API call (streaming or complete)
    6. Response parsing + audit logging
    """
    # ── Authentication ──────────────────────────────────────────────────────
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ").strip()

    extracted_org_id: str | None = None
    extracted_user_id: str | None = None

    if token != "dev-token":
        try:
            import base64
            import json as _json

            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            extracted_org_id = payload.get("organization_id") or payload.get("org_id")
            extracted_user_id = payload.get("sub") or payload.get("user_id")
        except Exception as jwt_err:
            logger.warning(f"Failed to decode JWT payload: {jwt_err}")

    # ── Resolve org_id (strict tenant isolation) ────────────────────────────
    if extracted_org_id and _UUID_RE.match(extracted_org_id):
        x_org_id = extracted_org_id
        logger.info(f"Using org_id from JWT: {x_org_id}")
    elif x_org_id and x_org_id != "default" and _UUID_RE.match(x_org_id):
        logger.info(f"Using org_id from X-Org-ID header: {x_org_id}")
    else:
        # Dev-mode fallback: use first org in DB
        from sqlalchemy import text as _text

        result = await db.execute(_text("SELECT id::text FROM organizations LIMIT 1"))
        row = result.first()
        if row:
            x_org_id = row[0]
            logger.warning(f"DEV MODE: falling back to first org {x_org_id}")
        else:
            raise HTTPException(
                status_code=401,
                detail="Cannot determine organization. Please log in again.",
            )

    # ── Resolve user_id ─────────────────────────────────────────────────────
    if extracted_user_id and _UUID_RE.match(extracted_user_id):
        user_id = extracted_user_id
    else:
        user_id = "550e8400-e29b-41d4-a716-446655440001"  # dev mode consistent UUID

    # ── Rate limiting ───────────────────────────────────────────────────────
    from ..services.rate_limiter import RateLimiter

    limiter = RateLimiter(redis)
    if not await limiter.check_query_rate(user_id, x_org_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    settings = get_copilot_settings_cached()

    # ── Execute RAG pipeline ────────────────────────────────────────────────
    from ..core.dependencies import _session_factory

    pipeline = RAGPipeline(settings, x_org_id, user_id, _session_factory)

    try:
        result = await pipeline.execute(query_request)

        # ── Streaming response ──────────────────────────────────────────────
        if query_request.stream:
            async def generate():
                full_response = []
                async for chunk in result:
                    full_response.append(chunk)
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"

                # Audit log after streaming completes
                if _UUID_RE.match(x_org_id) and _UUID_RE.match(user_id):
                    try:
                        provider = settings.llm_provider.lower()
                        model_used = _resolve_model_name(settings, provider)
                        from ..core.dependencies import _session_factory as sf
                        from ..repositories.query_log_repo import QueryLogRepository as QR
                        from cloudvisor_utils.database import rls_session
                        async with rls_session(sf, x_org_id) as audit_db:
                            await QR(audit_db).create(
                                organization_id=x_org_id,
                                user_id=user_id,
                                query_text=query_request.query,
                                intent="GENERAL",  # No longer using intent classification
                                response_text="".join(full_response),
                                citations=None,
                                data_sources=None,
                                processing_ms=None,
                                model_used=model_used,
                                context_finding_id=query_request.context.finding_id if query_request.context else None,
                                context_asset_id=query_request.context.asset_id if query_request.context else None,
                                was_streamed=True,
                            )
                    except Exception as audit_err:
                        logger.warning(f"Streaming audit log failed (non-critical): {audit_err}")

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        # ── Complete response audit log — always write, including direct answers ──
        try:
            provider = settings.llm_provider.lower()
            model_used = _resolve_model_name(settings, provider)
            if result.processing_ms and result.processing_ms < 1000:
                model_used = "direct"

            query_log_repo = QueryLogRepository(db)

            # ── Auto-create or reuse session ────────────────────────────────
            session_id = query_request.session_id if query_request.session_id else None

            if not session_id:
                # Auto-create a new session for this conversation
                from ..repositories.chat_session_repo import ChatSessionRepository
                session_repo = ChatSessionRepository(db)
                # Use first words of query as title
                title_words = query_request.query.strip().split()[:6]
                title = " ".join(title_words)
                if len(query_request.query.strip().split()) > 6:
                    title += "..."
                new_session = await session_repo.create(
                    organization_id=x_org_id,
                    user_id=user_id,
                    title=title,
                )
                session_id = new_session.id
                logger.info(f"Auto-created session: {session_id}")

            await query_log_repo.create(
                organization_id=x_org_id,
                user_id=user_id,
                query_text=query_request.query,
                intent=result.intent,
                response_text=result.answer,
                citations={"citations": [c.dict() for c in result.citations]},
                data_sources=result.data_sources_used,
                processing_ms=result.processing_ms,
                model_used=model_used,
                context_finding_id=query_request.context.finding_id if query_request.context else None,
                context_asset_id=query_request.context.asset_id if query_request.context else None,
                was_streamed=False,
                session_id=session_id,
            )

            # Update session message count
            from ..repositories.chat_session_repo import ChatSessionRepository
            session_repo = ChatSessionRepository(db)
            await session_repo.increment_message_count(session_id, x_org_id)

            # Return session_id in response so frontend can track it
            result.session_id = session_id

        except Exception as audit_err:
            logger.warning(f"Failed to write audit log (non-critical): {audit_err}")

        # ── Kafka event ─────────────────────────────────────────────────────
        try:
            from ..core.dependencies import _kafka_producer

            if _kafka_producer:
                await _kafka_producer.emit_query_logged(
                    query_id=result.query_id,
                    organization_id=x_org_id,
                    user_id=user_id,
                    intent="GENERAL",  # No longer using intent classification
                    processing_ms=result.processing_ms,
                    data_sources_used=result.data_sources_used,
                )
        except Exception as kafka_err:
            logger.warning(f"Failed to emit Kafka event (non-critical): {kafka_err}")

        return result

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}",
        )
    finally:
        await pipeline.close()


def _resolve_model_name(settings, provider: str) -> str:
    """Resolve the model name string from the active provider."""
    if provider == "ollama":
        return settings.ollama_model
    elif provider == "openrouter":
        return settings.openrouter_model
    elif provider in ("google", "gemini"):
        return settings.google_model
    elif provider == "openai":
        return settings.openai_model
    return provider


@router.get(
    "/history",
    summary="Get query history",
    description="Retrieve past queries for the current user's organization",
)
async def get_query_history(
    limit: int = 50,
    offset: int = 0,
    user_only: bool = True,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get query history.

    - user_only=true (default): returns only the current user's queries
    - user_only=false: returns all queries for the organization
    Returns full history: query, response, intent, model, latency, timestamps.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Extract org_id and user_id from JWT
    token = authorization.removeprefix("Bearer ").strip()
    extracted_org_id: str | None = None
    extracted_user_id: str | None = None

    if token != "dev-token":
        try:
            import base64
            import json as _json
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            extracted_org_id = payload.get("organization_id") or payload.get("org_id")
            extracted_user_id = payload.get("sub") or payload.get("user_id")
        except Exception:
            pass

    # Resolve org_id
    if extracted_org_id and _UUID_RE.match(extracted_org_id):
        org_id = extracted_org_id
    elif x_org_id and _UUID_RE.match(x_org_id):
        org_id = x_org_id
    else:
        # Dev fallback
        from sqlalchemy import text as _text
        result = await db.execute(_text("SELECT id::text FROM organizations LIMIT 1"))
        row = result.first()
        org_id = row[0] if row else None
        if not org_id:
            raise HTTPException(status_code=401, detail="Cannot determine organization.")

    # Resolve user_id
    user_id = None
    if user_only:
        if extracted_user_id and _UUID_RE.match(extracted_user_id):
            user_id = extracted_user_id
        # If user_id is placeholder, return org-level history anyway

    query_log_repo = QueryLogRepository(db)
    history = await query_log_repo.get_org_history(
        organization_id=org_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return {
        "queries": history,
        "total": len(history),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/history/{query_id}",
    summary="Get a single query by ID",
    description="Retrieve the full query and response for a specific query ID",
)
async def get_query_detail(
    query_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full detail for a single query including the complete response."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ").strip()
    extracted_org_id: str | None = None

    if token != "dev-token":
        try:
            import base64
            import json as _json
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            extracted_org_id = payload.get("organization_id") or payload.get("org_id")
        except Exception:
            pass

    if extracted_org_id and _UUID_RE.match(extracted_org_id):
        org_id = extracted_org_id
    elif x_org_id and _UUID_RE.match(x_org_id):
        org_id = x_org_id
    else:
        from sqlalchemy import text as _text
        result = await db.execute(_text("SELECT id::text FROM organizations LIMIT 1"))
        row = result.first()
        org_id = row[0] if row else None
        if not org_id:
            raise HTTPException(status_code=401, detail="Cannot determine organization.")

    query_log_repo = QueryLogRepository(db)
    entry = await query_log_repo.get_by_id(query_id, org_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Query not found")
    return entry
