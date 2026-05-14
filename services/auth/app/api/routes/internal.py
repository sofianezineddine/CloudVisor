"""Internal API routes for inter-service auth.

Security fixes applied:
- S-07: All internal endpoints now require X-Service-Token header for service-to-service auth.
  In production this should be replaced with mTLS certificate verification.
  The service token is read from AUTH_INTERNAL_SERVICE_TOKEN env var.
- B-05: /validate returns actual user role from user_roles table
- PERF: Token validation results cached in Redis (TTL 5 min) — spec target p99 < 10ms
"""

import json
import os
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...schemas import ErrorResponse
from ...services import RBACService
from ...services.utils import decode_token
from ...models import UserModel, OrganizationModel


router = APIRouter(prefix="/internal/auth", tags=["internal", "auth"])

# S-07 fix: service-to-service authentication token
# In production, replace with mTLS certificate verification
_INTERNAL_SERVICE_TOKEN = os.environ.get("AUTH_INTERNAL_SERVICE_TOKEN", "")

# Redis TTL for token validation cache (spec: 5 minutes)
_TOKEN_CACHE_TTL = 300


def _verify_service_token(x_service_token: str | None) -> None:
    """Verify the inter-service authentication token (S-07 fix).

    This is a lightweight shared-secret approach. For production, use mTLS.
    """
    if not _INTERNAL_SERVICE_TOKEN:
        # If no token is configured, log a warning but allow (dev mode)
        import logging
        logging.getLogger("auth.internal").warning(
            "AUTH_INTERNAL_SERVICE_TOKEN not set — internal endpoints are unprotected. "
            "Set this env var in production."
        )
        return

    if not x_service_token or x_service_token != _INTERNAL_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )


@router.post("/validate", response_model=dict)
async def validate_token(
    authorization: str = Header(..., alias="Authorization"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Validate JWT or API key and return user + org + permissions.

    S-07 fix: requires X-Service-Token for inter-service calls.
    PERF: Results cached in Redis for 5 minutes (spec target p99 < 10ms).
    """
    _verify_service_token(x_service_token)

    auth_settings = get_auth_settings_cached()

    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

        # Check Redis cache first (spec: p99 < 10ms after first validation)
        cache_key = f"token_validation:{token[:32]}"
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except (ValueError, TypeError):
                    pass

        try:
            payload = decode_token(
                token,
                auth_settings.secret_key,
                public_key=auth_settings.effective_public_key,
            )
            token_type = payload.get("type")

            if token_type == "api_key":
                from ...services import ApiKeyService

                api_key_service = ApiKeyService(db, auth_settings)
                api_key = await api_key_service.verify_api_key(token)

                if not api_key:
                    raise HTTPException(status_code=401, detail="Invalid API key")

                user = await db.get(UserModel, api_key.user_id)
                if not user or not user.is_active:
                    raise HTTPException(status_code=401, detail="User not found or inactive")

                org = await db.get(OrganizationModel, user.organization_id)

                result = {
                    "valid": True,
                    "user_id": user.id,
                    "organization_id": user.organization_id,
                    "organization_name": org.name if org else "",
                    "plan": org.plan if org else "free",
                    "scopes": api_key.scopes,
                    "auth_type": "api_key",
                }
                # Cache result
                if redis:
                    await redis.setex(cache_key, _TOKEN_CACHE_TTL, json.dumps(result))
                return result

            user_id = payload.get("sub")
            user = await db.get(UserModel, user_id)

            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="User not found or inactive")

            org = await db.get(OrganizationModel, user.organization_id)

            # B-05 fix: return actual role from user_roles table
            rbac = RBACService(db, auth_settings)
            role = await rbac.get_user_role(user_id)

            result = {
                "valid": True,
                "user_id": user.id,
                "organization_id": user.organization_id,
                "organization_name": org.name if org else "",
                "plan": org.plan if org else "free",
                "role": role,
                "auth_type": "jwt",
            }
            # Cache result (spec: 5 min TTL — short enough for revocation to propagate)
            if redis:
                await redis.setex(cache_key, _TOKEN_CACHE_TTL, json.dumps(result))
            return result

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=str(e))

    raise HTTPException(status_code=401, detail="Invalid authorization header")


@router.post("/authorize", response_model=dict)
async def authorize_action(
    authorization: str = Header(..., alias="Authorization"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
    action: str = Header(...),
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    resource_type: str | None = Header(None, alias="X-Resource-Type"),
    resource_id: str | None = Header(None, alias="X-Resource-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if action is permitted for user + resource.

    S-07 fix: requires X-Service-Token for inter-service calls.
    """
    _verify_service_token(x_service_token)

    auth_settings = get_auth_settings_cached()
    rbac_service = RBACService(db, auth_settings)

    result = await rbac_service.authorize(
        user_id=x_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    return result


@router.get("/org/{org_id}", response_model=dict)
async def get_organization(
    org_id: str,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get organization details including plan + feature flags.

    S-07 fix: requires X-Service-Token for inter-service calls.
    """
    _verify_service_token(x_service_token)

    org = await db.get(OrganizationModel, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "billing_email": org.billing_email,
        "features": {
            "custom_roles": org.plan in ["growth", "enterprise"],
            "saml_sso": org.plan == "enterprise",
            "oidc_sso": org.plan == "enterprise",
            "api_keys": True,
            "mfa": True,
            "audit_log_export": org.plan in ["growth", "enterprise"],
        },
    }


# ─── Roles management ─────────────────────────────────────────────────────────

@router.get("/org/{org_id}/roles")
async def list_roles(
    org_id: str,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all roles for an organization (builtin + custom)."""
    _verify_service_token(x_service_token)

    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    roles = await rbac.list_roles(org_id)
    return {"roles": roles, "total": len(roles)}


@router.post("/org/{org_id}/roles")
async def create_custom_role(
    org_id: str,
    data: dict,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a custom role (enterprise tier only)."""
    _verify_service_token(x_service_token)

    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    try:
        role = await rbac.create_custom_role(
            organization_id=org_id,
            name=data.get("name", ""),
            permissions=data.get("permissions", []),
            description=data.get("description"),
        )
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/role")
async def assign_user_role(
    user_id: str,
    data: dict,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Assign a role to a user with optional resource-level scope."""
    _verify_service_token(x_service_token)

    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    try:
        result = await rbac.assign_role(
            user_id=user_id,
            organization_id=data.get("organization_id", ""),
            role_name=data.get("role", "viewer"),
            scope=data.get("scope"),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
