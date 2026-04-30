"""
RBAC service — enforces role-based access control per spec §3.3.

Built-in roles (cannot be deleted or modified):
  owner              — All permissions including billing, org deletion
  admin              — All security permissions, user management, no billing
  security_engineer  — Read/write: findings, policies, suppressions, reports
  devops             — Read/write: CI/CD, IaC; read-only elsewhere
  viewer             — Read-only across all modules
  auditor            — Read-only + export compliance reports
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ─── Permission matrix ────────────────────────────────────────────────────────
# Format: { action_prefix: [roles_that_can_do_it] }
# Wildcards: "findings:*" covers findings:read, findings:write, findings:delete

ROLE_PERMISSIONS: dict[str, list[str]] = {
    # Full access
    "*": ["owner"],

    # All security operations
    "findings:*": ["owner", "admin", "security_engineer"],
    "findings:read": ["owner", "admin", "security_engineer", "devops", "viewer", "auditor"],
    "assets:read": ["owner", "admin", "security_engineer", "devops", "viewer", "auditor"],
    "assets:*": ["owner", "admin", "security_engineer"],
    "compliance:read": ["owner", "admin", "security_engineer", "viewer", "auditor"],
    "compliance:export": ["owner", "admin", "security_engineer", "auditor"],
    "rules:read": ["owner", "admin", "security_engineer", "devops", "viewer", "auditor"],
    "rules:write": ["owner", "admin", "security_engineer"],
    "rules:disable": ["owner", "admin", "security_engineer"],
    "suppressions:*": ["owner", "admin", "security_engineer"],
    "suppressions:read": ["owner", "admin", "security_engineer", "viewer", "auditor"],
    "incidents:*": ["owner", "admin", "security_engineer"],
    "incidents:read": ["owner", "admin", "security_engineer", "devops", "viewer", "auditor"],

    # CI/CD module
    "cicd:*": ["owner", "admin", "devops"],
    "cicd:read": ["owner", "admin", "devops", "security_engineer", "viewer", "auditor"],

    # Settings
    "accounts:read": ["owner", "admin", "security_engineer", "devops", "viewer", "auditor"],
    "accounts:write": ["owner", "admin"],
    "accounts:delete": ["owner", "admin"],
    "team:read": ["owner", "admin"],
    "team:write": ["owner", "admin"],
    "team:invite": ["owner", "admin"],
    "apikeys:read": ["owner", "admin", "security_engineer"],
    "apikeys:write": ["owner", "admin"],
    "notifications:*": ["owner", "admin"],
    "notifications:read": ["owner", "admin", "security_engineer"],

    # Billing — owner only
    "billing:*": ["owner"],

    # Reports
    "reports:read": ["owner", "admin", "security_engineer", "auditor"],
    "reports:generate": ["owner", "admin", "security_engineer", "auditor"],
}

# Actions that are always allowed for any authenticated user
ALWAYS_ALLOWED = {
    "auth:me",
    "auth:logout",
    "auth:mfa",
    "auth:sessions",
    "auth:apikeys:own",
}


class RBACService:
    """Role-Based Access Control service."""

    def __init__(self, db: AsyncSession, settings: Any):
        self._db = db
        self._settings = settings

    async def get_user_role(self, user_id: str) -> str:
        """Get the primary role for a user (checks user_roles table first, falls back to is_superuser)."""
        from sqlalchemy import select
        from ..models import UserModel
        from ..models.roles import UserRoleModel

        # Check user_roles table first (custom/assigned roles)
        role_result = await self._db.execute(
            select(UserRoleModel.role_name).where(
                UserRoleModel.user_id == user_id
            ).order_by(UserRoleModel.created_at.asc()).limit(1)
        )
        role_row = role_result.scalar_one_or_none()
        if role_row:
            return role_row

        # Fall back to is_superuser flag
        result = await self._db.execute(
            select(UserModel.is_superuser, UserModel.organization_id)
            .where(UserModel.id == user_id)
        )
        row = result.one_or_none()
        if not row:
            return "viewer"

        if row.is_superuser:
            return "owner"

        return self._settings.default_role if hasattr(self._settings, "default_role") else "security_engineer"

    async def assign_role(
        self,
        user_id: str,
        organization_id: str,
        role_name: str,
        scope: dict | None = None,
    ) -> dict:
        """Assign a role to a user with optional resource-level scope."""
        from ..models.roles import UserRoleModel

        # Validate role name
        valid_builtin = {"owner", "admin", "security_engineer", "devops", "viewer", "auditor"}
        if role_name not in valid_builtin:
            # Check if it's a custom role for this org
            from sqlalchemy import select
            from ..models.roles import RoleModel
            custom = await self._db.execute(
                select(RoleModel).where(
                    RoleModel.organization_id == organization_id,
                    RoleModel.name == role_name,
                )
            )
            if not custom.scalar_one_or_none():
                raise ValueError(f"Role '{role_name}' not found")

        # Remove existing role assignment for this user+org
        from sqlalchemy import delete
        await self._db.execute(
            delete(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.organization_id == organization_id,
            )
        )

        user_role = UserRoleModel(
            id=str(__import__("uuid").uuid4()),
            user_id=user_id,
            organization_id=organization_id,
            role_name=role_name,
            scope=scope,
            created_at=__import__("datetime").datetime.utcnow(),
        )
        self._db.add(user_role)
        await self._db.commit()

        return {"user_id": user_id, "role": role_name, "scope": scope}

    async def create_custom_role(
        self,
        organization_id: str,
        name: str,
        permissions: list[str],
        description: str | None = None,
    ) -> dict:
        """Create a custom role for an enterprise organization (enterprise tier only)."""
        from sqlalchemy import select
        from ..models import OrganizationModel
        from ..models.roles import RoleModel

        # Verify enterprise plan
        org = await self._db.get(OrganizationModel, organization_id)
        if not org or org.plan not in ("growth", "enterprise"):
            raise ValueError("Custom roles require growth or enterprise plan")

        # Check for duplicate name
        existing = await self._db.execute(
            select(RoleModel).where(
                RoleModel.organization_id == organization_id,
                RoleModel.name == name,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Role '{name}' already exists")

        role = RoleModel(
            id=str(__import__("uuid").uuid4()),
            organization_id=organization_id,
            name=name,
            description=description,
            permissions=permissions,
            is_builtin=False,
            is_default=False,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
        )
        self._db.add(role)
        await self._db.commit()
        await self._db.refresh(role)

        return role.to_dict()

    async def list_roles(self, organization_id: str) -> list[dict]:
        """List all roles available to an organization (builtin + custom)."""
        from ..models.roles import RoleModel
        from sqlalchemy import select

        # Built-in roles
        builtin_roles = [
            {"id": r, "name": r, "description": desc, "permissions": self._permissions_for_role(r),
             "is_builtin": True, "is_default": r == "viewer"}
            for r, desc in {
                "owner": "All permissions including billing and org management",
                "admin": "All security permissions, user management, no billing",
                "security_engineer": "Read/write findings, policies, suppressions, reports",
                "devops": "Read/write CI/CD and IaC; read-only elsewhere",
                "viewer": "Read-only across all modules",
                "auditor": "Read-only + export compliance reports",
            }.items()
        ]

        # Custom roles for this org
        result = await self._db.execute(
            select(RoleModel).where(RoleModel.organization_id == organization_id)
        )
        custom_roles = [r.to_dict() for r in result.scalars().all()]

        return builtin_roles + custom_roles

    async def get_user_permissions(self, user_id: str) -> list[str]:
        """Get all permissions for a user based on their role."""
        role = await self.get_user_role(user_id)
        return self._permissions_for_role(role)

    def _permissions_for_role(self, role: str) -> list[str]:
        """Return all actions this role can perform."""
        if role == "owner":
            return ["*"]

        perms = set()
        for action, allowed_roles in ROLE_PERMISSIONS.items():
            if role in allowed_roles:
                perms.add(action)

        return sorted(perms)

    async def check_permission(
        self,
        user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> bool:
        """
        Check if a user can perform an action.

        Action format: "resource_type:operation"
        Examples: "findings:read", "accounts:write", "billing:*"
        """
        # Always-allowed actions
        if action in ALWAYS_ALLOWED:
            return True

        role = await self.get_user_role(user_id)

        # Owner can do everything
        if role == "owner":
            return True

        # Check exact match
        allowed_roles = ROLE_PERMISSIONS.get(action, [])
        if role in allowed_roles:
            return True

        # Check wildcard: if "findings:read" is requested, check "findings:*"
        if ":" in action:
            resource_prefix = action.split(":")[0]
            wildcard = f"{resource_prefix}:*"
            wildcard_roles = ROLE_PERMISSIONS.get(wildcard, [])
            if role in wildcard_roles:
                return True

        # Check global wildcard
        if role in ROLE_PERMISSIONS.get("*", []):
            return True

        logger.debug(f"Permission denied: user={user_id} role={role} action={action}")
        return False

    async def authorize(
        self,
        user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        """Check authorization and return structured result."""
        role = await self.get_user_role(user_id)
        authorized = await self.check_permission(user_id, action, resource_type, resource_id)

        return {
            "authorized": authorized,
            "user_id": user_id,
            "role": role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
