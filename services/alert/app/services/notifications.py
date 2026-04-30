"""Notification service - routing and sending notifications."""

import uuid
import logging
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from ..models import NotificationChannelModel, NotificationLogModel

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for routing and sending notifications."""

    def __init__(self, db: AsyncSession, redis_client: Any = None):
        self._db = db
        self._redis = redis_client
        self._rate_limit = 10

    async def send_notification(
        self,
        finding: dict[str, Any],
    ) -> None:
        """Send notifications to configured channels."""
        organization_id = finding["organization_id"]
        severity = finding.get("severity", "MEDIUM")

        channels = await self._get_active_channels(organization_id)

        for channel in channels:
            if not self._channel_matches_severity(channel, severity):
                continue

            await self._send_to_channel(channel, finding)

    async def _get_active_channels(self, organization_id: str) -> list[NotificationChannelModel]:
        result = await self._db.execute(
            select(NotificationChannelModel).where(
                NotificationChannelModel.organization_id == organization_id,
                NotificationChannelModel.is_active == True,
            )
        )
        return list(result.scalars().all())

    def _channel_matches_severity(self, channel: NotificationChannelModel, severity: str) -> bool:
        if not channel.severity_filter:
            return True
        return severity in channel.severity_filter

    async def _send_to_channel(
        self, channel: NotificationChannelModel, finding: dict[str, Any]
    ) -> None:
        dedup_key = f"notif:{channel.id}:{finding['id']}"

        if self._redis:
            if await self._redis.exists(dedup_key):
                return
            await self._redis.setex(dedup_key, 300, "1")

        # Rate limiting via Redis
        from ..notifiers import check_rate_limit, get_notifier
        if not await check_rate_limit(channel.id, self._redis):
            logger.warning(f"Rate limit exceeded for channel {channel.id}, dropping notification")
            return

        try:
            # Use the notifier registry for Slack and webhook
            notifier = get_notifier(channel.channel_type)
            if notifier:
                channel_dict = {
                    "id": channel.id,
                    "channel_type": channel.channel_type,
                    "config": channel.config,
                }
                await notifier.send_with_retry(finding, channel_dict)
            elif channel.channel_type == "jira":
                await self._send_jira(channel.config, finding)
            elif channel.channel_type == "email":
                await self._send_email(channel.config, finding)

            await self._log_notification(channel.id, finding["id"], "sent")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            await self._log_notification(channel.id, finding["id"], "failed", str(e))

    async def _send_slack(self, config: dict, finding: dict) -> None:
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return

        payload = {
            "text": f":rotating_light: *{finding['severity']}* - {finding['title']}",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{finding['title']}*"}},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Severity:*\n{finding['severity']}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Resource:*\n{finding.get('resource_name', 'N/A')}",
                        },
                    ],
                },
            ],
        }

        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload)

    async def _send_jira(self, config: dict, finding: dict) -> None:
        logger.info(f"Would create Jira issue for finding: {finding['id']}")

    async def _send_email(self, config: dict, finding: dict) -> None:
        logger.info(f"Would send email for finding: {finding['id']}")

    async def _send_webhook(self, config: dict, finding: dict) -> None:
        webhook_url = config.get("url")
        if not webhook_url:
            return

        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=finding)

    async def _log_notification(
        self, channel_id: str, finding_id: str, status: str, error: str | None = None
    ) -> None:
        log = NotificationLogModel(
            id=str(uuid.uuid4()),
            finding_id=finding_id,
            channel_id=channel_id,
            status=status,
            error_message=error,
            sent_at=datetime.utcnow(),
        )
        self._db.add(log)
        await self._db.commit()


class ChannelService:
    """Service for managing notification channels."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_channel(
        self,
        organization_id: str,
        name: str,
        channel_type: str,
        config: dict[str, Any],
        severity_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        channel = NotificationChannelModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            name=name,
            channel_type=channel_type,
            config=config,
            severity_filter=severity_filter or [],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._db.add(channel)
        await self._db.commit()
        await self._db.refresh(channel)

        return self._channel_to_dict(channel)

    async def list_channels(self, organization_id: str) -> list[dict[str, Any]]:
        result = await self._db.execute(
            select(NotificationChannelModel).where(
                NotificationChannelModel.organization_id == organization_id
            )
        )
        return [self._channel_to_dict(c) for c in result.scalars().all()]

    async def update_channel(
        self,
        channel_id: str,
        name: str | None = None,
        is_active: bool | None = None,
        severity_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        result = await self._db.execute(
            select(NotificationChannelModel).where(NotificationChannelModel.id == channel_id)
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise ValueError("Channel not found")

        if name:
            channel.name = name
        if is_active is not None:
            channel.is_active = is_active
        if severity_filter:
            channel.severity_filter = severity_filter

        channel.updated_at = datetime.utcnow()
        await self._db.commit()

        return self._channel_to_dict(channel)

    async def delete_channel(self, channel_id: str) -> bool:
        result = await self._db.execute(
            select(NotificationChannelModel).where(NotificationChannelModel.id == channel_id)
        )
        channel = result.scalar_one_or_none()

        if not channel:
            return False

        await self._db.delete(channel)
        await self._db.commit()
        return True

    async def test_channel(self, channel_id: str) -> dict[str, Any]:
        result = await self._db.execute(
            select(NotificationChannelModel).where(NotificationChannelModel.id == channel_id)
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise ValueError("Channel not found")

        test_finding = {
            "id": "test-finding",
            "title": "Test Notification",
            "severity": "HIGH",
            "resource_name": "test-resource",
        }

        try:
            if channel.channel_type == "slack":
                await self._send_slack_test(channel.config, test_finding)
            return {"success": True, "message": "Test sent successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _send_slack_test(self, config: dict, finding: dict) -> None:
        webhook_url = config.get("webhook_url")
        if webhook_url:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json={"text": "Test from CloudVisor"})

    def _channel_to_dict(self, channel: NotificationChannelModel) -> dict[str, Any]:
        return {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type,
            "severity_filter": channel.severity_filter,
            "is_active": channel.is_active,
            "created_at": channel.created_at.isoformat(),
        }


