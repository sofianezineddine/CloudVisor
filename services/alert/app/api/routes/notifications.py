from fastapi import APIRouter, Depends, Query, Body

from app.core.dependencies import get_db
from app.schemas import ChannelCreateRequest, ChannelResponse
from app.services import ChannelService

router = APIRouter(prefix="/notifications/channels", tags=["notifications"])

# Separate router for test endpoint (no /channels prefix)
test_router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_channels(
    organization_id: str = Query(...),
    db=Depends(get_db),
) -> list[ChannelResponse]:
    service = ChannelService(db)
    channels = await service.list_channels(organization_id)
    return [ChannelResponse(**c) for c in channels]


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(
    data: ChannelCreateRequest,
    organization_id: str = Query(...),
    db=Depends(get_db),
) -> ChannelResponse:
    service = ChannelService(db)
    channel = await service.create_channel(
        organization_id, data.name, data.channel_type, data.config, data.severity_filter
    )
    return ChannelResponse(**channel)


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: str,
    db=Depends(get_db),
) -> dict:
    service = ChannelService(db)
    success = await service.delete_channel(channel_id)
    if not success:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Channel not found")
    return {"deleted": True}


@router.post("/{channel_id}/test")
async def test_channel(
    channel_id: str,
    db=Depends(get_db),
) -> dict:
    service = ChannelService(db)
    return await service.test_channel(channel_id)


@test_router.post("/test")
async def test_channel_by_body(
    body: dict = Body(...),
    db=Depends(get_db),
) -> dict:
    """Test a notification channel by channel_id in request body."""
    channel_id = body.get("channel_id")
    if not channel_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="channel_id is required")
    service = ChannelService(db)
    return await service.test_channel(channel_id)
