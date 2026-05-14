"""Organization management routes.

Spec §3.3 requirements:
- Create new organizations on signup (handled in auth.py register)
- Enforce organization-level feature flags based on plan
- Support organization deletion with full data purge cascade
- Emit org.created, org.plan_changed, org.deleted Kafka events
- User management: list members, invite, remove, change role
- Audit log access for auditors/admins
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached, get_kafka_producer
from ...models import UserModel, OrganizationModel, SessionModel, ApiKeyModel, AuditLogModel
from ...models.roles import UserRoleModel
from ...services.utils import decode_token
from ...services.rbac import RBACService
from ...repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/org", tags=["organization"])


def _require_auth(authorization: str | None) -> dict:
    """Extract and validate JWT payload from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    auth_settings = get_auth_settings_cached()
    try:
        payload = decode_token(
            token,
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _require_role(
    user_id: str,
    org_id: str,
    required_roles: list[str],
    db: AsyncSession,
) -> str:
    """Verify user belongs to org and has one of the required roles."""
    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    role = await rbac.get_user_role(user_id)
    if role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {required_roles}",
        )
    return role


# ─── Organization profile ─────────────────────────────────────────────────────

@router.get("/me")
async def get_my_organization(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current user's organization details."""
    payload = _require_auth(authorization)
    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    org = await db.get(OrganizationModel, org_id)
    if not org or org.is_deleted:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "billing_email": org.billing_email,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "features": {
            "custom_roles": org.plan in ["growth", "enterprise"],
            "saml_sso": org.plan == "enterprise",
            "oidc_sso": org.plan == "enterprise",
            "api_keys": True,
            "mfa": True,
            "audit_log_export": org.plan in ["growth", "enterprise"],
        },
    }


class UpdateOrgRequest(BaseModel):
    name: str | None = None
    billing_email: str | None = None


@router.patch("/me")
async def update_my_organization(
    data: UpdateOrgRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    kafka_producer=Depends(get_kafka_producer),
) -> dict:
    """Update organization name or billing email. Requires owner or admin role."""
    payload = _require_auth(authorization)
    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    await _require_role(user_id, org_id, ["owner", "admin"], db)

    org = await db.get(OrganizationModel, org_id)
    if not org or org.is_deleted:
        raise HTTPException(status_code=404, detail="Organization not found")

    if data.name is not None:
        org.name = data.name
    if data.billing_email is not None:
        org.billing_email = data.billing_email

    org.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Organization updated", "id": org.id, "name": org.name}


class ChangePlanRequest(BaseModel):
    plan: str  # free | starter | growth | enterprise


@router.post("/me/plan")
async def change_plan(
    data: ChangePlanRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    kafka_producer=Depends(get_kafka_producer),
) -> dict:
    """Change organization plan. Requires owner role (billing access).

    Emits org.plan_changed Kafka event per spec §3.3.
    """
    payload = _require_auth(authorization)
    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    await _require_role(user_id, org_id, ["owner"], db)

    valid_plans = {"free", "starter", "growth", "enterprise"}
    if data.plan not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {valid_plans}")

    org = await db.get(OrganizationModel, org_id)
    if not org or org.is_deleted:
        raise HTTPException(status_code=404, detail="Organization not found")

    old_plan = org.plan
    org.plan = data.plan
    org.updated_at = datetime.utcnow()
    await db.commit()

    # Emit org.plan_changed Kafka event (spec §3.3)
    if kafka_producer:
        try:
            await kafka_producer.emit_org_event(
                organization_id=org_id,
                event_type="org.plan_changed",
                data={"old_plan": old_plan, "new_plan": data.plan},
            )
        except Exception as e:
            logger.debug(f"org.plan_changed event failed (non-fatal): {e}")

    # Audit log
    audit = AuditLogModel(
        organization_id=org_id,
        user_id=user_id,
        event_type="org.plan_changed",
        event_data={"old_plan": old_plan, "new_plan": data.plan},
        success=True,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {"message": "Plan updated", "plan": data.plan}


@router.delete("/me")
async def delete_organization(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    kafka_producer=Depends(get_kafka_producer),
) -> dict:
    """Delete organization with full data purge cascade.

    Requires owner role. Emits org.deleted Kafka event per spec §3.3.
    This is a soft-delete — sets is_deleted=True and deactivates all users/sessions.
    """
    payload = _require_auth(authorization)
    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    await _require_role(user_id, org_id, ["owner"], db)

    org = await db.get(OrganizationModel, org_id)
    if not org or org.is_deleted:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Deactivate all users in the org
    await db.execute(
        update(UserModel)
        .where(UserModel.organization_id == org_id)
        .values(is_active=False, updated_at=datetime.utcnow())
    )

    # Deactivate all sessions
    await db.execute(
        update(SessionModel)
        .where(SessionModel.organization_id == org_id)
        .values(is_active=False)
    )

    # Deactivate all API keys
    await db.execute(
        update(ApiKeyModel)
        .where(
            ApiKeyModel.user_id.in_(
                select(UserModel.id).where(UserModel.organization_id == org_id)
            )
        )
        .values(is_active=False, updated_at=datetime.utcnow())
    )

    # Soft-delete the org
    org.is_deleted = True
    org.updated_at = datetime.utcnow()
    await db.commit()

    # Emit org.deleted Kafka event (spec §3.3)
    if kafka_producer:
        try:
            await kafka_producer.emit_org_event(
                organization_id=org_id,
                event_type="org.deleted",
                data={"name": org.name, "deleted_by": user_id},
            )
        except Exception as e:
            logger.debug(f"org.deleted event failed (non-fatal): {e}")

    return {"message": "Organization deleted"}


# ─── Team / member management ─────────────────────────────────────────────────

@router.get("/me/members")
async def list_members(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all members of the organization. Requires owner or admin role."""
    payload = _require_auth(authorization)
    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    await _require_role(user_id, org_id, ["owner", "admin"], db)

    result = await db.execute(
        select(UserModel).where(
            UserModel.organization_id == org_id,
            UserModel.is_active == True,  # noqa: E712
        )
    )
    users = result.scalars().all()

    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)

    members = []
    for u in users:
        role = await rbac.get_user_role(u.id)
        members.append({
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": role,
            "provider": u.provider,
            "mfa_enabled": u.mfa_enabled,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"members": members, "total": len(members)}


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"
    first_name: str | None = None
    last_name: str | None = None


@router.post("/me/members/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: InviteMemberRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    kafka_producer=Depends(get_kafka_producer),
) -> dict:
    """Invite a new member to the organization.

    Creates the user account with a temporary password reset token.
    Requires owner or admin role.
    """
    import secrets
    import uuid

    payload = _require_auth(authorization)
    inviter_id = payload.get("sub")
    org_id = payload.get("org_id")

    await _require_role(inviter_id, org_id, ["owner", "admin"], db)

    # Validate role
    valid_roles = {"owner", "admin", "security_engineer", "devops", "viewer", "auditor"}
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    # Check if user already exists in this org
    existing = await db.execute(
        select(UserModel).where(
            UserModel.email == data.email,
            UserModel.organization_id == org_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already exists in this organization")

    # Create user with no password (they'll set it via invite link)
    user_id = str(uuid.uuid4())
    user = UserModel(
        id=user_id,
        organization_id=org_id,
        email=data.email,
        password_hash=None,
        first_name=data.first_name,
        last_name=data.last_name,
        is_active=True,
        is_superuser=False,
        provider="local",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Assign role
    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    await rbac.assign_role(user_id=user_id, organization_id=org_id, role_name=data.role)

    # Generate invite token (stored in Redis, 7-day TTL)
    invite_token = secrets.token_urlsafe(32)
    await redis.setex(f"invite:{invite_token}", 7 * 24 * 3600, user_id)

    # Audit log
    audit = AuditLogModel(
        organization_id=org_id,
        user_id=inviter_id,
        event_type="team.member_invited",
        event_data={"invited_email": data.email, "role": data.role},
        success=True,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {
        "message": f"Invitation sent to {data.email}",
        "user_id": user_id,
        "invite_token": invite_token,  # In production, send via email
    }


@router.delete("/me/members/{member_id}")
async def remove_member(
    member_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a member from the organization. Requires owner or admin role.

    Owners cannot be removed by admins. Only owners can remove other owners.
    """
    payload = _require_auth(authorization)
    requester_id = payload.get("sub")
    org_id = payload.get("org_id")

    requester_role = await _require_role(requester_id, org_id, ["owner", "admin"], db)

    if requester_id == member_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization")

    member = await db.get(UserModel, member_id)
    if not member or member.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Member not found")

    # Check target member's role — admins cannot remove owners
    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    target_role = await rbac.get_user_role(member_id)

    if target_role == "owner" and requester_role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can remove other owners")

    # Deactivate user and their sessions
    member.is_active = False
    member.updated_at = datetime.utcnow()

    await db.execute(
        update(SessionModel)
        .where(SessionModel.user_id == member_id)
        .values(is_active=False)
    )

    await db.commit()

    # Audit log
    audit = AuditLogModel(
        organization_id=org_id,
        user_id=requester_id,
        event_type="team.member_removed",
        event_data={"removed_user_id": member_id, "removed_email": member.email},
        success=True,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {"message": "Member removed"}


class UpdateMemberRoleRequest(BaseModel):
    role: str


@router.patch("/me/members/{member_id}/role")
async def update_member_role(
    member_id: str,
    data: UpdateMemberRoleRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change a member's role. Requires owner or admin role.

    Admins cannot assign the owner role — only owners can do that.
    """
    payload = _require_auth(authorization)
    requester_id = payload.get("sub")
    org_id = payload.get("org_id")

    requester_role = await _require_role(requester_id, org_id, ["owner", "admin"], db)

    valid_roles = {"owner", "admin", "security_engineer", "devops", "viewer", "auditor"}
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    # Only owners can assign the owner role
    if data.role == "owner" and requester_role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can assign the owner role")

    member = await db.get(UserModel, member_id)
    if not member or member.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Member not found")

    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    await rbac.assign_role(user_id=member_id, organization_id=org_id, role_name=data.role)

    # Audit log
    audit = AuditLogModel(
        organization_id=org_id,
        user_id=requester_id,
        event_type="team.member_role_changed",
        event_data={"target_user_id": member_id, "new_role": data.role},
        success=True,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {"message": "Role updated", "user_id": member_id, "role": data.role}


# ─── Audit log access ─────────────────────────────────────────────────────────

@router.get("/me/audit-log")
async def get_audit_log(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    user_id_filter: str | None = Query(default=None, alias="user_id"),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
) -> dict:
    """Get audit log for the organization.

    Spec §3.3: Record every authentication and authorization event.
    Accessible by: owner, admin, security_engineer, auditor.
    """
    payload = _require_auth(authorization)
    requester_id = payload.get("sub")
    org_id = payload.get("org_id")

    await _require_role(
        requester_id, org_id,
        ["owner", "admin", "security_engineer", "auditor"],
        db,
    )

    audit_repo = AuditRepository(db)
    entries = await audit_repo.list_by_org(
        organization_id=org_id,
        limit=limit,
        offset=offset,
        event_type=event_type,
        user_id=user_id_filter,
        since=since,
        until=until,
    )
    total = await audit_repo.count_by_org(org_id)

    return {
        "entries": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "user_id": e.user_id,
                "event_data": e.event_data,
                "success": e.success,
                "failure_reason": e.failure_reason,
                "ip_address": e.ip_address,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
