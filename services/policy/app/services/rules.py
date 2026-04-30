"""Rule management service."""

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RuleModel, RuleDisableModel
from ..opa import OPAService, RegoParser


logger = logging.getLogger(__name__)


class RuleManagementService:
    """Service for managing rules."""

    def __init__(
        self,
        db: AsyncSession,
        opa_service: OPAService,
    ):
        self._db = db
        self._opa = opa_service
        self._parser = RegoParser()

    async def get_rules(
        self,
        organization_id: str | None = None,
        category: str | None = None,
        provider: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all rules with optional filtering."""
        query = select(RuleModel)

        if organization_id:
            # Include built-in rules (org_id IS NULL) + org-specific custom rules
            from sqlalchemy import or_
            query = query.where(
                or_(
                    RuleModel.organization_id == None,
                    RuleModel.organization_id == organization_id,
                )
            )
        else:
            query = query.where(RuleModel.organization_id == None)

        if category:
            query = query.where(RuleModel.category == category)

        if provider:
            query = query.where(RuleModel.provider == provider)

        if severity:
            query = query.where(RuleModel.severity == severity)

        result = await self._db.execute(query)
        rules = result.scalars().all()

        return [self._rule_to_dict(rule) for rule in rules]

    async def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Get a specific rule."""
        result = await self._db.execute(select(RuleModel).where(RuleModel.rule_id == rule_id))
        rule = result.scalar_one_or_none()

        if rule:
            return self._rule_to_dict(rule)
        return None

    async def create_custom_rule(
        self,
        organization_id: str,
        rego_code: str,
        title: str,
        description: str | None = None,
        severity: str = "MEDIUM",
        category: str = "custom",
        remediation: str | None = None,
        compliance_mapping: list[dict] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a custom rule for an organization."""
        validation = await self._opa.validate_rego(rego_code)

        if not validation.get("valid"):
            raise ValueError(f"Invalid Rego: {validation.get('error')}")

        metadata = self._parser.extract_metadata(rego_code)

        rule_id = f"custom-{uuid.uuid4().hex[:8]}"

        rule = RuleModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            rule_id=rule_id,
            title=title or metadata.get("title", title),
            description=description or metadata.get("description"),
            severity=severity or metadata.get("severity", "MEDIUM"),
            category=category,
            remediation=remediation or metadata.get("remediation"),
            rego_code=rego_code,
            version="1.0.0",
            compliance_mapping=compliance_mapping or [],
            tags=tags or [],
            is_builtin=False,
            is_custom=True,
            is_enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._db.add(rule)
        await self._db.commit()
        await self._db.refresh(rule)

        policy_name = f"custom.{organization_id}.{rule_id}"
        await self._opa.load_policy(policy_name, rego_code, metadata)

        logger.info(f"Created custom rule: {rule_id} for org {organization_id}")

        return self._rule_to_dict(rule)

    async def update_custom_rule(
        self,
        rule_id: str,
        organization_id: str,
        rego_code: str | None = None,
        title: str | None = None,
        description: str | None = None,
        remediation: str | None = None,
        compliance_mapping: list[dict] | None = None,
    ) -> dict[str, Any] | None:
        """Update a custom rule."""
        result = await self._db.execute(
            select(RuleModel).where(
                RuleModel.rule_id == rule_id,
                RuleModel.organization_id == organization_id,
                RuleModel.is_custom == True,
            )
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return None

        if rego_code:
            validation = await self._opa.validate_rego(rego_code)
            if not validation.get("valid"):
                raise ValueError(f"Invalid Rego: {validation.get('error')}")
            rule.rego_code = rego_code
            rule.version = self._increment_version(rule.version)

        if title:
            rule.title = title
        if description:
            rule.description = description
        if remediation:
            rule.remediation = remediation
        if compliance_mapping:
            rule.compliance_mapping = compliance_mapping

        rule.updated_at = datetime.utcnow()
        await self._db.commit()
        await self._db.refresh(rule)

        policy_name = f"custom.{organization_id}.{rule_id}"
        metadata = self._parser.extract_metadata(rego_code or rule.rego_code)
        await self._opa.load_policy(policy_name, rule.rego_code, metadata)

        return self._rule_to_dict(rule)

    async def delete_custom_rule(
        self,
        rule_id: str,
        organization_id: str,
    ) -> bool:
        """Delete a custom rule."""
        result = await self._db.execute(
            select(RuleModel).where(
                RuleModel.rule_id == rule_id,
                RuleModel.organization_id == organization_id,
                RuleModel.is_custom == True,
            )
        )
        rule = result.scalar_one_or_none()

        if not rule:
            return False

        policy_name = f"custom.{organization_id}.{rule_id}"
        await self._opa.delete_policy(policy_name)

        await self._db.delete(rule)
        await self._db.commit()

        return True

    async def disable_rule(
        self,
        rule_id: str,
        organization_id: str,
        reason: str | None,
        disabled_by: str,
        expires_at: datetime | None = None,
    ) -> bool:
        """Disable a rule for an organization."""
        result = await self._db.execute(select(RuleModel).where(RuleModel.rule_id == rule_id))
        rule = result.scalar_one_or_none()

        if not rule:
            return False

        disable = RuleDisableModel(
            id=str(uuid.uuid4()),
            rule_id=rule_id,
            organization_id=organization_id,
            reason=reason,
            disabled_by=disabled_by,
            disabled_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        self._db.add(disable)
        await self._db.commit()

        return True

    async def enable_rule(
        self,
        rule_id: str,
        organization_id: str,
    ) -> bool:
        """Re-enable a previously disabled rule."""
        result = await self._db.execute(
            select(RuleDisableModel).where(
                RuleDisableModel.rule_id == rule_id,
                RuleDisableModel.organization_id == organization_id,
            )
        )
        disable = result.scalars().all()

        for d in disable:
            await self._db.delete(d)

        await self._db.commit()
        return True

    def _rule_to_dict(self, rule: RuleModel) -> dict[str, Any]:
        """Convert rule model to dict."""
        return {
            "id": rule.id,
            "rule_id": rule.rule_id,
            "title": rule.title,
            "description": rule.description,
            "severity": rule.severity,
            "category": rule.category,
            "provider": rule.provider,
            "resource_type": rule.resource_type,
            "remediation": rule.remediation,
            "version": rule.version,
            "compliance_mapping": rule.compliance_mapping,
            "tags": rule.tags,
            "is_builtin": rule.is_builtin,
            "is_custom": rule.is_custom,
            "is_enabled": rule.is_enabled,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat(),
        }

    def _increment_version(self, version: str) -> str:
        """Increment version string."""
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return ".".join(parts)
        return "1.0.1"
