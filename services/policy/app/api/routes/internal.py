"""Internal API routes for service-to-service communication."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis, get_policy_settings_cached
from app.opa import OPAService
from app.services import PolicyEvaluationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/policy", tags=["internal"])


class InternalEvaluateRequest(BaseModel):
    resources: list[dict[str, Any]]
    org_id: str
    category: str | None = None


class InternalEvaluateResponse(BaseModel):
    findings: list[dict[str, Any]]
    evaluated_count: int


@router.post("/evaluate", response_model=InternalEvaluateResponse)
async def internal_evaluate(
    data: InternalEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> InternalEvaluateResponse:
    """Internal endpoint for CSPM scanner to evaluate resources against policy rules."""
    try:
        policy_settings = get_policy_settings_cached()
        opa_service = OPAService(policy_settings.opa_url)
        eval_service = PolicyEvaluationService(db, opa_service, redis)
        findings = await eval_service.evaluate_resources(
            resources=data.resources,
            organization_id=data.org_id,
            category=data.category or "cspm",
        )
        return InternalEvaluateResponse(
            findings=findings,
            evaluated_count=len(data.resources),
        )
    except Exception as e:
        logger.error(f"Internal evaluate error: {e}")
        return InternalEvaluateResponse(findings=[], evaluated_count=len(data.resources))
