from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_db
from app.schemas import SuppressionCreateRequest, ChannelCreateRequest, ChannelResponse
from app.services import SuppressionService, ChannelService

router = APIRouter(prefix="/suppressions", tags=["suppressions"])


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
    organization_id: str = Query(...),
    db=Depends(get_db),
) -> dict:
    service = SuppressionService(db)
    return await service.create_rule(
        organization_id=organization_id,
        rule_id=data.rule_id,
        resource_tag_key=data.resource_tag_key,
        resource_tag_value=data.resource_tag_value,
        account_id=data.account_id,
        region=data.region,
        reason=data.reason,
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
