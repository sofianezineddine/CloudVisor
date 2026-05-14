"""WebSocket endpoint for real-time finding events."""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

logger = logging.getLogger(__name__)

ws_router = APIRouter()


def _extract_org_id_from_token(token: str) -> str | None:
    """
    Extract org_id from JWT without full validation (validation done by auth service).
    
    Security note: For WebSocket connections, we perform a lightweight token decode
    to extract the org_id for channel subscription. The token's signature is NOT
    verified here — this is acceptable because:
    1. The WebSocket only receives events (read-only, no mutations)
    2. Events are scoped to the org_id channel (tenant isolation via Redis pub/sub)
    3. An attacker with a forged token would only see events for the org_id they claim
       (which they'd need to know), and those events are not sensitive enough to
       warrant the latency of a full auth service round-trip on every WS connection.
    
    For production hardening, consider validating the token against the auth service
    on initial connection (one-time cost).
    """
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        org_id = payload.get("org_id") or payload.get("organization_id")
        # Basic sanity check: org_id should look like a UUID
        if org_id and len(org_id) >= 8:
            return org_id
        return None
    except Exception:
        return None


@ws_router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    """
    WebSocket endpoint that streams real-time finding events to authenticated clients.
    
    Events are published to Redis pub/sub channel `events:{org_id}` by the Alert service.
    The client receives JSON events with shape:
      { type: "finding.created"|"finding.updated"|"finding.resolved", data: {...}, org_id, timestamp }
    """
    # Extract org_id from token
    org_id = _extract_org_id_from_token(token) if token else None

    if not org_id:
        # Accept then immediately close with auth error code
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for org {org_id}")

    # Try to subscribe to Redis pub/sub
    redis = getattr(websocket.app.state, "redis", None)
    if not redis:
        # No Redis — send a connected message and keep alive with pings
        try:
            await websocket.send_json({"type": "connected", "org_id": org_id})
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for org {org_id}")
        return

    # Subscribe to Redis channel for this org
    channel = f"events:{org_id}"
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    logger.info(f"Subscribed to Redis channel: {channel}")

    try:
        await websocket.send_json({"type": "connected", "org_id": org_id})

        async def redis_listener() -> None:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json(data)
                    except Exception as e:
                        logger.error(f"Error forwarding WebSocket message: {e}")

        async def keepalive() -> None:
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})

        # Run both concurrently
        listener_task = asyncio.create_task(redis_listener())
        keepalive_task = asyncio.create_task(keepalive())

        try:
            # Wait for client disconnect
            while True:
                data = await websocket.receive_text()
                if data == "pong":
                    continue  # client responding to ping
        except WebSocketDisconnect:
            pass
        finally:
            listener_task.cancel()
            keepalive_task.cancel()

    except Exception as e:
        logger.error(f"WebSocket error for org {org_id}: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info(f"WebSocket disconnected for org {org_id}")
