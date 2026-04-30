"""Suppression service - auto-suppress matching findings."""

import uuid
import logging
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SuppressionRuleModel, FindingModel

logger = logging.getLogger(__name__)


class SuppressionService:
    """Service for managing suppression rules."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_rule(
        self,
        organization_id: str,
        rule_id: str | None = None,
        resource_tag_key: str | None = None,
        resource_tag_value: str | None = None,
        account_id: str | None = None,
        region: str | None = None,
        reason: str | None = None,
        created_by: str = "system",
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        """Create a suppression rule."""
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + __import__("datetime").timedelta(days=expires_in_days)

        rule = SuppressionRuleModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            rule_id=rule_id,
            resource_tag_key=resource_tag_key,
            resource_tag_value=resource_tag_value,
            account_id=account_id,
            region=region,
            reason=reason,
            created_by=created_by,
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        self._db.add(rule)
        await self._db.commit()
        await self._db.refresh(rule)

        return self._rule_to_dict(rule)

    async def check_suppression(
        self,
        finding: dict[str, Any],
    ) -> bool:
        """Check if a finding matches any suppression rule."""
        org_id = finding.get("organization_id")

        result = await self._db.execute(
            select(SuppressionRuleModel).where(
                SuppressionRuleModel.organization_id == org_id,
                SuppressionRuleModel.is_active == True,
            )
        )
        rules = result.scalars().all()

        for rule in rules:
            if rule.expires_at and rule.expires_at < datetime.utcnow():
                continue

            if self._matches_rule(finding, rule):
                logger.info(f"Finding {finding['id']} suppressed by rule {rule.id}")
                return True

        return False

    def _matches_rule(self, finding: dict, rule: SuppressionRuleModel) -> bool:
        if rule.rule_id and finding.get("rule_id") != rule.rule_id:
            return False

        if rule.account_id and finding.get("account_id") != rule.account_id:
            return False

        if rule.region and finding.get("region") != rule.region:
            return False

        if rule.resource_tag_key:
            tags = finding.get("tags", {})
            if not isinstance(tags, dict):
                return False
            if tags.get(rule.resource_tag_key) != rule.resource_tag_value:
                return False

        return True

    async def list_rules(self, organization_id: str) -> list[dict[str, Any]]:
        result = await self._db.execute(
            select(SuppressionRuleModel).where(
                SuppressionRuleModel.organization_id == organization_id
            )
        )
        return [self._rule_to_dict(r) for r in result.scalars().all()]

    async def delete_rule(self, rule_id: str, organization_id: str) -> bool:
        result = await self._db.execute(
            select(SuppressionRuleModel).where(
                SuppressionRuleModel.id == rule_id,
                SuppressionRuleModel.organization_id == organization_id,
            )
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return False

        await self._db.delete(rule)
        await self._db.commit()
        return True

    def _rule_to_dict(self, rule: SuppressionRuleModel) -> dict[str, Any]:
        return {
            "id": rule.id,
            "organization_id": rule.organization_id,
            "rule_id": rule.rule_id,
            "resource_tag_key": rule.resource_tag_key,
            "resource_tag_value": rule.resource_tag_value,
            "account_id": rule.account_id,
            "region": rule.region,
            "reason": rule.reason,
            "created_by": rule.created_by,
            "expires_at": rule.expires_at.isoformat() if rule.expires_at else None,
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat(),
        }
