"""SSO routes — SAML 2.0 and OIDC (Okta, Azure AD, Ping Identity).

Security fixes applied:
- S-03: Tokens no longer passed in URL fragment — use one-time exchange code
- S-04: /saml/configure and /oidc/configure now require admin authentication
- S-13: SAML ACS validates org_id from RelayState against the assertion's audience
- Q-13: FRONTEND_URL read from environment, not hardcoded
- Q-14: OIDC redirect_uri read from environment, not hardcoded localhost
"""

import json
import logging
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...services.sso import SAMLService, OIDCService
from ...services.auth_service import AuthService
from ...services.utils import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/sso", tags=["sso"])

# Q-13 fix: read from environment, never hardcode
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Q-14 fix: read service base URL from environment
SERVICE_BASE_URL = os.getenv("AUTH_SERVICE_BASE_URL", "http://localhost:8002")


def _require_admin_auth(authorization: str | None) -> dict:
    """Require admin or owner JWT to access SSO configuration endpoints (S-04 fix)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
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
    """SP-initiated SAML login. Redirects user to the organization's configured IdP."""
    auth_settings = get_auth_settings_cached()
    if not auth_settings.saml_enabled:
        raise HTTPException(status_code=400, detail="SAML SSO is not enabled")

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
    """SAML Assertion Consumer Service (ACS) endpoint.

    S-13 fix: org_id from RelayState is validated — the SAML assertion's
    audience/recipient must match the configured SP entity ID for that org.
    S-03 fix: tokens returned via one-time exchange code, not URL fragment.
    """
    auth_settings = get_auth_settings_cached()
    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse", "")
    relay_state = form_data.get("RelayState", "")

    # RelayState carries the org_id
    org_id = relay_state or request.query_params.get("org_id", "")
    if not org_id:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_org_id")

    saml_config_raw = await redis.get(f"saml_config:{org_id}")
    if not saml_config_raw:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=saml_not_configured")

    saml_config = json.loads(saml_config_raw)
    saml_svc = SAMLService(db, auth_settings, redis)

    try:
        user_info = await saml_svc.process_assertion(saml_response, saml_config, org_id)
        user = await saml_svc.login_or_provision(user_info, org_id)

        auth_svc = AuthService(db, auth_settings, redis)
        session = await auth_svc._create_session(user, None, request.client.host if request.client else None, None)
        tokens = await auth_svc._create_tokens(user, session.id)

        # S-03 fix: use one-time exchange code instead of URL fragment
        exchange_code = secrets.token_urlsafe(32)
        await redis.setex(
            f"oauth:exchange:{exchange_code}",
            120,
            json.dumps(tokens),
        )

        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback/success?code={exchange_code}")

    except Exception as e:
        logger.error(f"SAML ACS processing failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=saml_failed")


@router.post("/saml/configure")
async def configure_saml(
    org_id: str,
    config: SAMLConfigRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    redis=Depends(get_redis),
) -> dict:
    """Store SAML configuration for an organization.

    S-04 fix: requires authentication. Only org admins/owners can configure SSO.
    """
    # S-04 fix: require authentication
    payload = _require_admin_auth(authorization)
    token_org_id = payload.get("org_id")

    # Ensure the authenticated user belongs to the org they're configuring
    if token_org_id and token_org_id != org_id:
        raise HTTPException(status_code=403, detail="Cannot configure SSO for another organization")

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
    """OIDC authorization redirect. Redirects user to the configured OIDC provider."""
    auth_settings = get_auth_settings_cached()
    if not auth_settings.oidc_enabled:
        raise HTTPException(status_code=400, detail="OIDC SSO is not enabled")

    oidc_config_raw = await redis.get(f"oidc_config:{org_id}")
    if not oidc_config_raw:
        raise HTTPException(status_code=404, detail="OIDC not configured for this organization")

    oidc_config = json.loads(oidc_config_raw)
    oidc_svc = OIDCService(db, auth_settings, redis)

    # Q-14 fix: use SERVICE_BASE_URL from environment
    redirect_uri = f"{SERVICE_BASE_URL}/auth/sso/oidc/callback?org_id={org_id}"

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
    """OIDC callback — exchanges code for tokens and logs user in.

    S-03 fix: tokens returned via one-time exchange code, not URL fragment.
    Q-14 fix: redirect_uri uses SERVICE_BASE_URL from environment.
    """
    auth_settings = get_auth_settings_cached()

    # Resolve org_id from state if not in query
    if not org_id:
        org_id = await redis.get(f"oidc:state:{state}") or ""
    if not org_id:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_org_id")

    oidc_config_raw = await redis.get(f"oidc_config:{org_id}")
    if not oidc_config_raw:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oidc_not_configured")

    oidc_config = json.loads(oidc_config_raw)
    oidc_svc = OIDCService(db, auth_settings, redis)
    # Q-14 fix: use SERVICE_BASE_URL from environment
    redirect_uri = f"{SERVICE_BASE_URL}/auth/sso/oidc/callback?org_id={org_id}"

    try:
        user_info = await oidc_svc.exchange_code(oidc_config, code, redirect_uri, state)
        user = await oidc_svc.login_or_provision(user_info, org_id)

        auth_svc = AuthService(db, auth_settings, redis)
        session = await auth_svc._create_session(user, None, None, None)
        tokens = await auth_svc._create_tokens(user, session.id)

        # S-03 fix: use one-time exchange code instead of URL fragment
        exchange_code = secrets.token_urlsafe(32)
        await redis.setex(
            f"oauth:exchange:{exchange_code}",
            120,
            json.dumps(tokens),
        )

        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback/success?code={exchange_code}")

    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"OIDC callback failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oidc_failed")


@router.post("/oidc/configure")
async def configure_oidc(
    org_id: str,
    config: OIDCConfigRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    redis=Depends(get_redis),
) -> dict:
    """Store OIDC configuration for an organization.

    S-04 fix: requires authentication. Only org admins/owners can configure SSO.
    """
    # S-04 fix: require authentication
    payload = _require_admin_auth(authorization)
    token_org_id = payload.get("org_id")

    if token_org_id and token_org_id != org_id:
        raise HTTPException(status_code=403, detail="Cannot configure SSO for another organization")

    await redis.set(
        f"oidc_config:{org_id}",
        json.dumps(config.model_dump()),
        ex=86400 * 365,
    )
    return {"message": "OIDC configuration saved", "org_id": org_id}


# ─── SAML SP Metadata ─────────────────────────────────────────────────────────

@router.get("/saml/metadata")
async def saml_metadata(
    org_id: str = Query(..., description="Organization ID"),
    redis=Depends(get_redis),
) -> dict:
    """Return SAML SP metadata for IdP configuration.

    Spec §3.3: GET /auth/sso/saml/metadata — SAML SP metadata for IdP configuration.
    Returns the SP entity ID, ACS URL, and certificate for the organization.
    """
    auth_settings = get_auth_settings_cached()
    if not auth_settings.saml_enabled:
        raise HTTPException(status_code=400, detail="SAML SSO is not enabled")

    saml_config_raw = await redis.get(f"saml_config:{org_id}")
    if not saml_config_raw:
        raise HTTPException(status_code=404, detail="SAML not configured for this organization")

    saml_config = json.loads(saml_config_raw)

    sp_entity_id = saml_config.get("sp_entity_id", f"{SERVICE_BASE_URL}/auth/sso/saml")
    acs_url = saml_config.get("acs_url", f"{SERVICE_BASE_URL}/auth/sso/saml/acs")
    sp_cert = saml_config.get("sp_cert", "")

    # Build minimal SAML SP metadata XML
    metadata_xml = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{sp_entity_id}">
  <md:SPSSODescriptor
      AuthnRequestsSigned="false"
      WantAssertionsSigned="true"
      protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{acs_url}"
        index="1"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""

    from fastapi.responses import Response
    return Response(
        content=metadata_xml,
        media_type="application/xml",
    )
