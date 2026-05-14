"""Organization repository — all organization-related DB queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OrganizationModel


class OrganizationRepository:
    """Database access layer for organizations."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, org_id: str) -> OrganizationModel | None:
        """Get organization by ID."""
        return await self._db.get(OrganizationModel, org_id)

    async def get_by_slug(self, slug: str) -> OrganizationModel | None:
        """Get organization by slug."""
        result = await self._db.execute(
            select(OrganizationModel).where(OrganizationModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Check if a slug is already taken."""
        result = await self._db.execute(
            select(OrganizationModel.id).where(OrganizationModel.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def create(self, **kwargs: Any) -> OrganizationModel:
        """Create a new organization."""
        org = OrganizationModel(**kwargs)
        self._db.add(org)
        await self._db.commit()
        await self._db.refresh(org)
        return org

    async def update_plan(self, org_id: str, plan: str) -> OrganizationModel | None:
        """Update organization plan (triggers org.plan_changed event in service layer)."""
        org = await self.get_by_id(org_id)
        if not org:
            return None
        org.plan = plan
        org.updated_at = datetime.utcnow()
        await self._db.commit()
        await self._db.refresh(org)
        return org

    async def soft_delete(self, org_id: str) -> bool:
        """Soft-delete an organization (sets is_deleted=True)."""
        org = await self.get_by_id(org_id)
        if not org:
            return False
        org.is_deleted = True
        org.updated_at = datetime.utcnow()
        await self._db.commit()
        return True
