"""Repository for cloud account data access."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.cloud_account import CloudAccountModel

logger = logging.getLogger(__name__)


class AccountRepository:
    """Data access layer for cloud accounts."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, account_id: str) -> CloudAccountModel | None:
        """Get a cloud account by its internal UUID."""
        result = await self._session.execute(
            select(CloudAccountModel).where(CloudAccountModel.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self, account_id: str, organization_id: str
    ) -> CloudAccountModel | None:
        """Get a cloud account by ID scoped to an organization."""
        result = await self._session.execute(
            select(CloudAccountModel).where(
                CloudAccountModel.id == account_id,
                CloudAccountModel.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_provider_account(
        self, organization_id: str, provider: str, cloud_account_id: str
    ) -> CloudAccountModel | None:
        """Get a cloud account by provider + cloud account ID (e.g. AWS account ID)."""
        result = await self._session.execute(
            select(CloudAccountModel).where(
                CloudAccountModel.organization_id == organization_id,
                CloudAccountModel.provider == provider,
                CloudAccountModel.account_id == cloud_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        provider: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CloudAccountModel]:
        """List cloud accounts for an organization with optional filters."""
        stmt = select(CloudAccountModel).where(
            CloudAccountModel.organization_id == organization_id
        )
        if provider:
            stmt = stmt.where(CloudAccountModel.provider == provider)
        if status:
            stmt = stmt.where(CloudAccountModel.status == status)
        stmt = stmt.order_by(CloudAccountModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_active(self) -> list[CloudAccountModel]:
        """List all active accounts across all organizations (used by scheduler)."""
        result = await self._session.execute(
            select(CloudAccountModel).where(
                CloudAccountModel.status.in_(["active", "pending"])
            )
        )
        return list(result.scalars().all())

    async def count_by_org(self, organization_id: str) -> int:
        """Count cloud accounts for an organization."""
        result = await self._session.execute(
            select(func.count()).select_from(CloudAccountModel).where(
                CloudAccountModel.organization_id == organization_id
            )
        )
        return result.scalar() or 0

    async def create(self, account: CloudAccountModel) -> CloudAccountModel:
        """Persist a new cloud account."""
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def update_status(
        self,
        account_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update account status and optional error message."""
        values: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(
            update(CloudAccountModel)
            .where(CloudAccountModel.id == account_id)
            .values(**values)
        )

    async def update_sync_result(
        self,
        account_id: str,
        success: bool,
        resource_count: int | None = None,
        error_message: str | None = None,
        consecutive_errors: int | None = None,
    ) -> None:
        """Update sync-related fields after a sync completes."""
        now = datetime.utcnow()
        values: dict[str, Any] = {
            "last_sync_at": now,
            "updated_at": now,
        }
        if success:
            values["last_successful_sync_at"] = now
            values["consecutive_errors"] = 0
            values["sync_status"] = "idle"
            values["error_message"] = None
            if resource_count is not None:
                values["resource_count"] = resource_count
        else:
            values["sync_status"] = "error"
            if error_message:
                values["error_message"] = error_message
            if consecutive_errors is not None:
                values["consecutive_errors"] = consecutive_errors

        await self._session.execute(
            update(CloudAccountModel)
            .where(CloudAccountModel.id == account_id)
            .values(**values)
        )

    async def update_polling_interval(
        self, account_id: str, interval_minutes: int
    ) -> None:
        """Update the polling interval for an account."""
        await self._session.execute(
            update(CloudAccountModel)
            .where(CloudAccountModel.id == account_id)
            .values(polling_interval_minutes=interval_minutes, updated_at=datetime.utcnow())
        )

    async def delete(self, account_id: str) -> bool:
        """Delete a cloud account. Returns True if a row was deleted."""
        account = await self.get_by_id(account_id)
        if not account:
            return False
        await self._session.delete(account)
        await self._session.flush()
        return True
