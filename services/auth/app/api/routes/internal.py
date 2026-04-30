"""Internal API routes for inter-service auth."""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.dependencies import get_db, get_auth_settings_cached
from ...schemas import ErrorResponse
from ...services import RBACService
from ...services.utils import decode_token
from ...models import UserModel, OrganizationModel


router = APIRouter(prefix="/internal/auth", tags=["internal", "auth"])


@router.post("/validate", response_model=dict)
async def validate_token(
    authorization: str = Header(..., alias="Authorization"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate JWT or API key and return user + org + permissions."""
    auth_settings = get_auth_settings_cached()

    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")

        try:
            payload = decode_token(token, auth_settings.secret_key)
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

                return {
                    "valid": True,
                    "user_id": user.id,
                    "organization_id": user.organization_id,
                    "organization_name": org.name if org else "",
                    "plan": org.plan if org else "free",
                    "scopes": api_key.scopes,
                }

            user_id = payload.get("sub")
            user = await db.get(UserModel, user_id)

            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="User not found or inactive")

            org = await db.get(OrganizationModel, user.organization_id)

            return {
                "valid": True,
                "user_id": user.id,
                "organization_id": user.organization_id,
                "organization_name": org.name if org else "",
                "plan": org.plan if org else "free",
            }

        except Exception as e:
            raise HTTPException(status_code=401, detail=str(e))

    raise HTTPException(status_code=401, detail="Invalid authorization header")


@router.post("/authorize", response_model=dict)
async def authorize_action(
    authorization: str = Header(..., alias="Authorization"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
    action: str = Header(...),
    resource_type: str | None = Header(None, alias="X-Resource-Type"),
    resource_id: str | None = Header(None, alias="X-Resource-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if action is permitted for user + resource."""
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get organization details including plan + feature flags."""
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all roles for an organization (builtin + custom)."""
    auth_settings = get_auth_settings_cached()
    rbac = RBACService(db, auth_settings)
    roles = await rbac.list_roles(org_id)
    return {"roles": roles, "total": len(roles)}


@router.post("/org/{org_id}/roles")
async def create_custom_role(
    org_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a custom role (enterprise tier only)."""
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Assign a role to a user with optional resource-level scope."""
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
