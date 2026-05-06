"""Metrics aggregation service - pre-computed Redis counters for dashboard."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Service for maintaining pre-aggregated metrics in Redis per spec:
    - Findings by severity (real-time)
    - Findings by module, account, region
    - Trend data: new findings per day (last 90 days)
    - MTTR (mean time to resolve) per severity
    """

    def __init__(self, redis_client: Any):
        self._redis = redis_client

    async def increment_finding_counter(
        self,
        organization_id: str,
        severity: str,
        status: str,
        provider: str | None = None,
        account_id: str | None = None,
        region: str | None = None,
    ) -> None:
        """Increment finding counters in Redis."""
        if not self._redis:
            return

        try:
            # Overall counters
            await self._redis.hincrby(f"metrics:{organization_id}:severity", severity, 1)
            await self._redis.hincrby(f"metrics:{organization_id}:status", status, 1)

            # By provider
            if provider:
                await self._redis.hincrby(
                    f"metrics:{organization_id}:provider", provider, 1
                )

            # By account
            if account_id:
                await self._redis.hincrby(
                    f"metrics:{organization_id}:account", account_id, 1
                )

            # By region
            if region:
                await self._redis.hincrby(f"metrics:{organization_id}:region", region, 1)

            # Daily trend (for last 90 days)
            today = datetime.utcnow().strftime("%Y-%m-%d")
            await self._redis.hincrby(
                f"metrics:{organization_id}:daily_new", today, 1
            )
            await self._redis.expire(
                f"metrics:{organization_id}:daily_new", 90 * 24 * 3600
            )

        except Exception as e:
            logger.error(f"Failed to increment metrics: {e}")

    async def decrement_finding_counter(
        self,
        organization_id: str,
        severity: str,
        old_status: str,
        provider: str | None = None,
        account_id: str | None = None,
        region: str | None = None,
    ) -> None:
        """Decrement finding counters when status changes."""
        if not self._redis:
            return

        try:
            await self._redis.hincrby(
                f"metrics:{organization_id}:severity", severity, -1
            )
            await self._redis.hincrby(
                f"metrics:{organization_id}:status", old_status, -1
            )

            if provider:
                await self._redis.hincrby(
                    f"metrics:{organization_id}:provider", provider, -1
                )

            if account_id:
                await self._redis.hincrby(
                    f"metrics:{organization_id}:account", account_id, -1
                )

            if region:
                await self._redis.hincrby(
                    f"metrics:{organization_id}:region", region, -1
                )

        except Exception as e:
            logger.error(f"Failed to decrement metrics: {e}")

    async def update_status_counter(
        self, organization_id: str, old_status: str, new_status: str
    ) -> None:
        """Update status counters when finding status changes."""
        if not self._redis:
            return

        try:
            await self._redis.hincrby(
                f"metrics:{organization_id}:status", old_status, -1
            )
            await self._redis.hincrby(
                f"metrics:{organization_id}:status", new_status, 1
            )
        except Exception as e:
            logger.error(f"Failed to update status metrics: {e}")

    async def record_resolution(
        self,
        organization_id: str,
        severity: str,
        time_to_resolve_hours: float,
    ) -> None:
        """Record resolution time for MTTR calculation."""
        if not self._redis:
            return

        try:
            key = f"metrics:{organization_id}:mttr:{severity}"
            # Store last 1000 resolution times
            await self._redis.lpush(key, time_to_resolve_hours)
            await self._redis.ltrim(key, 0, 999)
            await self._redis.expire(key, 90 * 24 * 3600)
        except Exception as e:
            logger.error(f"Failed to record resolution time: {e}")

    async def get_dashboard_metrics(self, organization_id: str) -> dict[str, Any]:
        """Get pre-aggregated metrics for dashboard."""
        if not self._redis:
            return {}

        try:
            # Get all counters
            severity_counts = await self._redis.hgetall(
                f"metrics:{organization_id}:severity"
            )
            status_counts = await self._redis.hgetall(
                f"metrics:{organization_id}:status"
            )
            provider_counts = await self._redis.hgetall(
                f"metrics:{organization_id}:provider"
            )
            account_counts = await self._redis.hgetall(
                f"metrics:{organization_id}:account"
            )
            region_counts = await self._redis.hgetall(
                f"metrics:{organization_id}:region"
            )

            # Get daily trend (last 30 days)
            daily_new = await self._redis.hgetall(
                f"metrics:{organization_id}:daily_new"
            )

            # Compute MTTR per severity
            mttr = {}
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                times = await self._redis.lrange(
                    f"metrics:{organization_id}:mttr:{severity}", 0, -1
                )
                if times:
                    avg = sum(float(t) for t in times) / len(times)
                    mttr[severity] = round(avg, 2)

            return {
                "by_severity": {k: int(v) for k, v in severity_counts.items()},
                "by_status": {k: int(v) for k, v in status_counts.items()},
                "by_provider": {k: int(v) for k, v in provider_counts.items()},
                "by_account": {k: int(v) for k, v in account_counts.items()},
                "by_region": {k: int(v) for k, v in region_counts.items()},
                "daily_new": {k: int(v) for k, v in daily_new.items()},
                "mttr_hours": mttr,
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {}

    async def rebuild_metrics(self, organization_id: str, findings: list) -> None:
        """Rebuild all metrics from scratch (for data consistency)."""
        if not self._redis:
            return

        try:
            # Clear existing metrics
            keys = await self._redis.keys(f"metrics:{organization_id}:*")
            if keys:
                await self._redis.delete(*keys)

            # Rebuild from findings
            for finding in findings:
                await self.increment_finding_counter(
                    organization_id=organization_id,
                    severity=finding.get("severity"),
                    status=finding.get("status"),
                    provider=finding.get("provider"),
                    account_id=finding.get("account_id"),
                    region=finding.get("region"),
                )

            logger.info(f"Rebuilt metrics for org {organization_id}")

        except Exception as e:
            logger.error(f"Failed to rebuild metrics: {e}")
