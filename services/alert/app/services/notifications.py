"""Notification service - routing and sending notifications."""

import uuid
import logging
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import NotificationChannelModel, NotificationLogModel

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for routing and sending notifications."""

    def __init__(self, db: AsyncSession, redis_client: Any = None, kafka_producer: Any = None):
        self._db = db
        self._redis = redis_client
        self._producer = kafka_producer
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
            if not self._channel_matches_filters(channel, finding):
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

    def _channel_matches_filters(
        self, channel: NotificationChannelModel, finding: dict[str, Any]
    ) -> bool:
        """Check if finding matches all channel routing filters."""
        # Severity filter
        if channel.severity_filter:
            if finding.get("severity") not in channel.severity_filter:
                return False

        # Module filter (based on rule_id prefix, e.g., "cspm.", "cwpp.")
        if channel.module_filter:
            rule_id = finding.get("rule_id", "")
            module = rule_id.split(".")[0] if "." in rule_id else ""
            if module not in channel.module_filter:
                return False

        # Account filter
        if channel.account_filter:
            if finding.get("account_id") not in channel.account_filter:
                return False

        # Tag filter (finding must have all specified tags)
        if channel.tag_filter:
            finding_tags = finding.get("tags", {})
            if not isinstance(finding_tags, dict):
                return False
            for key, value in channel.tag_filter.items():
                if finding_tags.get(key) != value:
                    return False

        return True

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
            # Use the notifier registry for all channel types
            notifier = get_notifier(channel.channel_type)
            if notifier:
                channel_dict = {
                    "id": channel.id,
                    "channel_type": channel.channel_type,
                    "config": channel.config,
                }
                await notifier.send_with_retry(finding, channel_dict)
            else:
                logger.warning(f"No notifier found for channel type: {channel.channel_type}")

            await self._log_notification(channel.id, finding["id"], "sent")
            # Emit notification.sent Kafka event per spec §3.5
            await self._emit_kafka("notification.sent", {
                "event_type": "notification.sent",
                "finding_id": finding["id"],
                "channel_id": channel.id,
                "channel_type": channel.channel_type,
                "organization_id": finding.get("organization_id"),
                "severity": finding.get("severity"),
            })

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            await self._log_notification(channel.id, finding["id"], "failed", str(e))
            # Emit notification.failed Kafka event per spec §3.5
            await self._emit_kafka("notification.failed", {
                "event_type": "notification.failed",
                "finding_id": finding["id"],
                "channel_id": channel.id,
                "channel_type": channel.channel_type,
                "organization_id": finding.get("organization_id"),
                "error": str(e),
            })

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

    async def _emit_kafka(self, topic: str, event: dict[str, Any]) -> None:
        """Emit Kafka event. Non-fatal if producer unavailable."""
        if not self._producer:
            return
        try:
            import json as _json
            from datetime import datetime as _dt
            event.setdefault("timestamp", _dt.utcnow().isoformat())
            await self._producer.send_and_wait(
                topic,
                value=_json.dumps(event, default=str).encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Failed to emit {topic}: {e}")


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
        module_filter: list[str] | None = None,
        account_filter: list[str] | None = None,
        tag_filter: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        channel = NotificationChannelModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            name=name,
            channel_type=channel_type,
            config=config,
            severity_filter=severity_filter or [],
            module_filter=module_filter or [],
            account_filter=account_filter or [],
            tag_filter=tag_filter or {},
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
        config: dict[str, Any] | None = None,
        is_active: bool | None = None,
        severity_filter: list[str] | None = None,
        module_filter: list[str] | None = None,
        account_filter: list[str] | None = None,
        tag_filter: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        result = await self._db.execute(
            select(NotificationChannelModel).where(NotificationChannelModel.id == channel_id)
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise ValueError("Channel not found")

        if name:
            channel.name = name
        if config is not None:
            channel.config = config
        if is_active is not None:
            channel.is_active = is_active
        if severity_filter is not None:
            channel.severity_filter = severity_filter
        if module_filter is not None:
            channel.module_filter = module_filter
        if account_filter is not None:
            channel.account_filter = account_filter
        if tag_filter is not None:
            channel.tag_filter = tag_filter

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
            "id": "test-finding-000",
            "organization_id": channel.organization_id,
            "title": "Test Notification from CloudVisor",
            "severity": "HIGH",
            "resource_name": "test-resource",
            "resource_id": "test-resource-id",
            "account_id": "test-account",
            "region": "us-east-1",
            "provider": "aws",
            "description": "This is a test notification to verify your channel configuration.",
            "remediation": "No action required — this is a test.",
        }

        try:
            from ..notifiers import get_notifier
            notifier = get_notifier(channel.channel_type)
            if not notifier:
                return {"success": False, "message": f"No notifier for channel type: {channel.channel_type}"}

            channel_dict = {
                "id": channel.id,
                "channel_type": channel.channel_type,
                "config": channel.config,
            }
            success = await notifier.send(test_finding, channel_dict)
            if success:
                return {"success": True, "message": "Test notification sent successfully"}
            else:
                return {"success": False, "message": "Notifier returned failure — check channel configuration"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _channel_to_dict(self, channel: NotificationChannelModel) -> dict[str, Any]:
        return {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type,
            "severity_filter": channel.severity_filter,
            "module_filter": channel.module_filter or [],
            "account_filter": channel.account_filter or [],
            "is_active": channel.is_active,
            "created_at": channel.created_at.isoformat(),
        }


