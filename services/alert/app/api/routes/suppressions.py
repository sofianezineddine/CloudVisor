from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import get_db
from app.schemas import SuppressionCreateRequest, ChannelCreateRequest, ChannelResponse
from app.services import SuppressionService, ChannelService

router = APIRouter(prefix="/suppressions", tags=["suppressions"])


def _extract_user_id(request: Request) -> str:
    """Extract user ID from JWT Bearer token for audit logging."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import base64, json
            token = auth[7:]
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                return payload.get("sub", "unknown")
        except Exception:
            pass
    return request.headers.get("X-User-ID", "unknown")


@router.get("")
async def list_suppressions(
    organization_id: str = Query(...),
    db=Depends(get_db),
) -> list:
    service = SuppressionService(db)
    return await service.list_rules(organization_id)


@router.post("")
async def create_suppression(
    data: SuppressionCreateRequest,
    request: Request,
    organization_id: str = Query(...),
    db=Depends(get_db),
) -> dict:
    """Create a suppression rule. Records the user who created it."""
    user_id = _extract_user_id(request)
    service = SuppressionService(db)
    return await service.create_rule(
        organization_id=organization_id,
        rule_id=data.rule_id,
        resource_tag_key=data.resource_tag_key,
        resource_tag_value=data.resource_tag_value,
        account_id=data.account_id,
        region=data.region,
        reason=data.reason,
        created_by=user_id,  # Fixed: use actual user ID, not hardcoded "system"
        expires_in_days=data.expires_in_days,
    )


@router.delete("/{rule_id}")
async def delete_suppression(
    rule_id: str,
    organization_id: str = Query(...),
    db=Depends(get_db),
) -> dict:
    service = SuppressionService(db)
    success = await service.delete_rule(rule_id, organization_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"deleted": True}
