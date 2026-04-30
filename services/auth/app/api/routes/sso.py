"""SSO routes — SAML 2.0 and OIDC (Okta, Azure AD, Ping Identity)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...services.sso import SAMLService, OIDCService
from ...services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/sso", tags=["sso"])

FRONTEND_URL = "http://localhost:3000"


# ─── SAML 2.0 ─────────────────────────────────────────────────────────────────

class SAMLConfigRequest(BaseModel):
    """SAML configuration for an organization."""
    idp_entity_id: str
    idp_sso_url: str
    idp_cert: str
    sp_entity_id: str = "https://app.cloudvisor.io"
    acs_url: str = "https://app.cloudvisor.io/auth/sso/saml/acs"
    idp_slo_url: str = ""
    sp_cert: str = ""
    sp_private_key: str = ""


@router.get("/saml/login")
async def saml_login(
    org_id: str = Query(..., description="Organization ID for SAML SSO"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """
    SP-initiated SAML login.
    Redirects user to the organization's configured IdP.
    """
    auth_settings = get_auth_settings_cached()
    if not auth_settings.saml_enabled:
        raise HTTPException(status_code=400, detail="SAML SSO is not enabled")

    # Load org SAML config from Redis (stored when org configures SSO)
    import json
    saml_config_raw = await redis.get(f"saml_config:{org_id}")
    if not saml_config_raw:
        raise HTTPException(status_code=404, detail="SAML not configured for this organization")

    saml_config = json.loads(saml_config_raw)
    saml_svc = SAMLService(db, auth_settings, redis)

    try:
        redirect_url = await saml_svc.initiate_login(saml_config)
        return RedirectResponse(url=redirect_url)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"SAML login initiation failed: {e}")
        raise HTTPException(status_code=500, detail="SAML login failed")


@router.post("/saml/acs")
async def saml_acs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """
    SAML Assertion Consumer Service (ACS) endpoint.
    Receives SAML response from IdP and logs the user in.
    """
    auth_settings = get_auth_settings_cached()
    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse", "")
    relay_state = form_data.get("RelayState", "")

    # RelayState carries the org_id
    org_id = relay_state or request.query_params.get("org_id", "")
    if not org_id:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_org_id")

    import json
    saml_config_raw = await redis.get(f"saml_config:{org_id}")
    if not saml_config_raw:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=saml_not_configured")

    saml_config = json.loads(saml_config_raw)
    saml_svc = SAMLService(db, auth_settings, redis)

    try:
        user_info = await saml_svc.process_assertion(saml_response, saml_config, org_id)
        user = await saml_svc.login_or_provision(user_info, org_id)

        auth_svc = AuthService(db, auth_settings, redis)
        session = await auth_svc._create_session(user, None, None, None)
        tokens = await auth_svc._create_tokens(user, session.id)

        redirect_url = (
            f"{FRONTEND_URL}/auth/callback/success"
            f"#access_token={tokens['access_token']}"
            f"&refresh_token={tokens['refresh_token']}"
            f"&token_type={tokens['token_type']}"
        )
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"SAML ACS processing failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=saml_failed")


@router.post("/saml/configure")
async def configure_saml(
    org_id: str,
    config: SAMLConfigRequest,
    redis=Depends(get_redis),
) -> dict:
    """
    Store SAML configuration for an organization.
    Called by org admins when setting up SSO.
    """
    import json
    await redis.set(
        f"saml_config:{org_id}",
        json.dumps(config.model_dump()),
        ex=86400 * 365,  # 1 year TTL
    )
    return {"message": "SAML configuration saved", "org_id": org_id}


# ─── OIDC ─────────────────────────────────────────────────────────────────────

class OIDCConfigRequest(BaseModel):
    """OIDC configuration for an organization."""
    issuer: str
    client_id: str
    client_secret: str
    scopes: str = "openid email profile"
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""


@router.get("/oidc/login")
async def oidc_login(
    org_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """
    OIDC authorization redirect.
    Redirects user to the configured OIDC provider.
    """
    auth_settings = get_auth_settings_cached()
    if not auth_settings.oidc_enabled:
        raise HTTPException(status_code=400, detail="OIDC SSO is not enabled")

    import json
    oidc_config_raw = await redis.get(f"oidc_config:{org_id}")
    if not oidc_config_raw:
        raise HTTPException(status_code=404, detail="OIDC not configured for this organization")

    oidc_config = json.loads(oidc_config_raw)
    oidc_svc = OIDCService(db, auth_settings, redis)

    redirect_uri = f"http://localhost:8002/auth/sso/oidc/callback?org_id={org_id}"

    try:
        auth_url, state = await oidc_svc.get_authorization_url(oidc_config, redirect_uri)
        # Store org_id in Redis keyed by state
        await redis.setex(f"oidc:state:{state}", 600, org_id)
        return RedirectResponse(url=auth_url)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"OIDC login initiation failed: {e}")
        raise HTTPException(status_code=500, detail="OIDC login failed")


@router.get("/oidc/callback")
async def oidc_callback(
    code: str = Query(...),
    state: str = Query(...),
    org_id: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """
    OIDC callback — exchanges code for tokens and logs user in.
    """
    auth_settings = get_auth_settings_cached()

    # Resolve org_id from state if not in query
    if not org_id:
        org_id = await redis.get(f"oidc:state:{state}") or ""
    if not org_id:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_org_id")

    import json
    oidc_config_raw = await redis.get(f"oidc_config:{org_id}")
    if not oidc_config_raw:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oidc_not_configured")

    oidc_config = json.loads(oidc_config_raw)
    oidc_svc = OIDCService(db, auth_settings, redis)
    redirect_uri = f"http://localhost:8002/auth/sso/oidc/callback?org_id={org_id}"

    try:
        user_info = await oidc_svc.exchange_code(oidc_config, code, redirect_uri, state)
        user = await oidc_svc.login_or_provision(user_info, org_id)

        auth_svc = AuthService(db, auth_settings, redis)
        session = await auth_svc._create_session(user, None, None, None)
        tokens = await auth_svc._create_tokens(user, session.id)

        redirect_url = (
            f"{FRONTEND_URL}/auth/callback/success"
            f"#access_token={tokens['access_token']}"
            f"&refresh_token={tokens['refresh_token']}"
            f"&token_type={tokens['token_type']}"
        )
        return RedirectResponse(url=redirect_url)

    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"OIDC callback failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oidc_failed")


@router.post("/oidc/configure")
async def configure_oidc(
    org_id: str,
    config: OIDCConfigRequest,
    redis=Depends(get_redis),
) -> dict:
    """Store OIDC configuration for an organization."""
    import json
    await redis.set(
        f"oidc_config:{org_id}",
        json.dumps(config.model_dump()),
        ex=86400 * 365,
    )
    return {"message": "OIDC configuration saved", "org_id": org_id}
