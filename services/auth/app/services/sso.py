"""SSO service — SAML 2.0 and OIDC (Okta, Azure AD, Ping Identity).

SAML 2.0:
  - SP-initiated flow: CloudVisor redirects user to IdP
  - IdP-initiated flow: IdP posts assertion to CloudVisor ACS endpoint
  - Uses python3-saml library

OIDC:
  - Authorization Code flow with PKCE
  - Supports any OIDC-compliant provider (Okta, Azure AD, Ping, etc.)
  - Uses authlib library
"""

import logging
import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserModel, OrganizationModel

logger = logging.getLogger(__name__)


# ─── SAML 2.0 ─────────────────────────────────────────────────────────────────

class SAMLService:
    """SAML 2.0 SSO service for enterprise customers."""

    def __init__(self, db: AsyncSession, settings: Any, redis_client: Any = None):
        self._db = db
        self._settings = settings
        self._redis = redis_client

    def _get_saml_settings(self, org_saml_config: dict) -> dict:
        """Build python3-saml settings dict from org config."""
        sp_entity_id = org_saml_config.get("sp_entity_id", "https://app.cloudvisor.io")
        acs_url = org_saml_config.get("acs_url", "https://app.cloudvisor.io/auth/saml/acs")

        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": sp_entity_id,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": f"{sp_entity_id}/slo",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": org_saml_config.get("sp_cert", ""),
                "privateKey": org_saml_config.get("sp_private_key", ""),
            },
            "idp": {
                "entityId": org_saml_config.get("idp_entity_id", ""),
                "singleSignOnService": {
                    "url": org_saml_config.get("idp_sso_url", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": org_saml_config.get("idp_slo_url", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": org_saml_config.get("idp_cert", ""),
            },
        }

    async def initiate_login(self, org_saml_config: dict) -> str:
        """
        SP-initiated SAML login.
        Returns the redirect URL to the IdP.
        """
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth

            saml_settings = self._get_saml_settings(org_saml_config)
            # Build a minimal request dict for python3-saml
            req = {
                "https": "on",
                "http_host": "app.cloudvisor.io",
                "script_name": "/auth/saml/login",
                "server_port": "443",
                "get_data": {},
                "post_data": {},
            }
            auth = OneLogin_Saml2_Auth(req, saml_settings)
            return auth.login()
        except ImportError:
            raise RuntimeError(
                "python3-saml not installed. Add 'python3-saml' to requirements.txt"
            )

    async def process_assertion(
        self,
        saml_response: str,
        org_saml_config: dict,
        organization_id: str,
    ) -> dict[str, Any]:
        """
        Process SAML assertion from IdP (ACS endpoint handler).
        Returns user info extracted from the assertion.
        """
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            import base64

            saml_settings = self._get_saml_settings(org_saml_config)
            req = {
                "https": "on",
                "http_host": "app.cloudvisor.io",
                "script_name": "/auth/saml/acs",
                "server_port": "443",
                "get_data": {},
                "post_data": {"SAMLResponse": saml_response},
            }
            auth = OneLogin_Saml2_Auth(req, saml_settings)
            auth.process_response()

            errors = auth.get_errors()
            if errors:
                raise ValueError(f"SAML assertion errors: {errors}")

            if not auth.is_authenticated():
                raise ValueError("SAML authentication failed")

            # Extract attributes from assertion
            attrs = auth.get_attributes()
            name_id = auth.get_nameid()

            email = name_id
            if not email:
                email = (
                    attrs.get("email", [None])[0]
                    or attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", [None])[0]
                )

            first_name = (
                attrs.get("firstName", [None])[0]
                or attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname", [None])[0]
                or ""
            )
            last_name = (
                attrs.get("lastName", [None])[0]
                or attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname", [None])[0]
                or ""
            )
            role = attrs.get("role", [None])[0] or attrs.get("groups", [None])[0]

            if not email:
                raise ValueError("Email not found in SAML assertion")

            return {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "provider": "saml",
                "provider_id": name_id,
            }

        except ImportError:
            raise RuntimeError("python3-saml not installed")

    async def login_or_provision(
        self,
        user_info: dict[str, Any],
        organization_id: str,
    ) -> UserModel:
        """
        Find or create a user from SAML assertion data.
        Enterprise orgs can auto-provision users on first SSO login (JIT provisioning).
        """
        email = user_info["email"]

        result = await self._db.execute(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.organization_id == organization_id,
            )
        )
        user = result.scalar_one_or_none()

        if user:
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            await self._db.commit()
            return user

        # JIT provisioning: create user on first SSO login
        user = UserModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            email=email,
            password_hash=None,
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            is_active=True,
            is_superuser=False,
            provider="saml",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login_at=datetime.utcnow(),
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)

        logger.info(f"JIT provisioned SAML user: {email} in org {organization_id}")
        return user


# ─── OIDC ─────────────────────────────────────────────────────────────────────

class OIDCService:
    """OIDC SSO service — supports Okta, Azure AD, Ping Identity, any OIDC provider."""

    def __init__(self, db: AsyncSession, settings: Any, redis_client: Any = None):
        self._db = db
        self._settings = settings
        self._redis = redis_client

    async def get_authorization_url(
        self,
        oidc_config: dict,
        redirect_uri: str,
        state: str | None = None,
    ) -> tuple[str, str]:
        """
        Build the OIDC authorization URL.
        Returns (authorization_url, state).
        """
        try:
            from authlib.integrations.httpx_client import AsyncOAuth2Client

            client = AsyncOAuth2Client(
                client_id=oidc_config["client_id"],
                client_secret=oidc_config["client_secret"],
                scope=oidc_config.get("scopes", "openid email profile"),
            )

            state = state or secrets.token_urlsafe(16)
            code_verifier = secrets.token_urlsafe(32)
            code_challenge = self._generate_code_challenge(code_verifier)

            # Store code_verifier in Redis for PKCE verification
            if self._redis:
                await self._redis.setex(
                    f"oidc:pkce:{state}",
                    600,  # 10 min TTL
                    code_verifier,
                )

            authorization_endpoint = oidc_config.get("authorization_endpoint")
            if not authorization_endpoint:
                # Discover from well-known endpoint
                authorization_endpoint = await self._discover_endpoint(
                    oidc_config["issuer"], "authorization_endpoint"
                )

            url, _ = client.create_authorization_url(
                authorization_endpoint,
                redirect_uri=redirect_uri,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            )

            return url, state

        except ImportError:
            raise RuntimeError("authlib not installed. Add 'authlib' to requirements.txt")

    async def exchange_code(
        self,
        oidc_config: dict,
        code: str,
        redirect_uri: str,
        state: str,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for tokens and return user info.
        """
        try:
            from authlib.integrations.httpx_client import AsyncOAuth2Client
            import httpx

            # Retrieve PKCE code_verifier
            code_verifier = None
            if self._redis:
                code_verifier = await self._redis.get(f"oidc:pkce:{state}")
                await self._redis.delete(f"oidc:pkce:{state}")

            token_endpoint = oidc_config.get("token_endpoint")
            if not token_endpoint:
                token_endpoint = await self._discover_endpoint(
                    oidc_config["issuer"], "token_endpoint"
                )

            userinfo_endpoint = oidc_config.get("userinfo_endpoint")
            if not userinfo_endpoint:
                userinfo_endpoint = await self._discover_endpoint(
                    oidc_config["issuer"], "userinfo_endpoint"
                )

            client = AsyncOAuth2Client(
                client_id=oidc_config["client_id"],
                client_secret=oidc_config["client_secret"],
            )

            token = await client.fetch_token(
                token_endpoint,
                code=code,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
            )

            # Fetch user info
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token['access_token']}"},
                )
                userinfo = resp.json()

            email = userinfo.get("email")
            if not email:
                raise ValueError("Email not found in OIDC userinfo")

            return {
                "email": email,
                "first_name": userinfo.get("given_name", ""),
                "last_name": userinfo.get("family_name", ""),
                "provider": "oidc",
                "provider_id": userinfo.get("sub", email),
                "raw": userinfo,
            }

        except ImportError:
            raise RuntimeError("authlib not installed")

    async def login_or_provision(
        self,
        user_info: dict[str, Any],
        organization_id: str,
    ) -> UserModel:
        """Find or JIT-provision a user from OIDC token data."""
        email = user_info["email"]

        result = await self._db.execute(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.organization_id == organization_id,
            )
        )
        user = result.scalar_one_or_none()

        if user:
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            await self._db.commit()
            return user

        # JIT provisioning
        user = UserModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            email=email,
            password_hash=None,
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            is_active=True,
            is_superuser=False,
            provider="oidc",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login_at=datetime.utcnow(),
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)

        logger.info(f"JIT provisioned OIDC user: {email} in org {organization_id}")
        return user

    @staticmethod
    def _generate_code_challenge(code_verifier: str) -> str:
        """Generate PKCE code challenge from verifier (S256 method)."""
        import hashlib
        import base64
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    @staticmethod
    async def _discover_endpoint(issuer: str, endpoint_name: str) -> str:
        """Discover OIDC endpoint from well-known configuration."""
        import httpx
        well_known_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            resp = await client.get(well_known_url)
            config = resp.json()
        endpoint = config.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"OIDC endpoint '{endpoint_name}' not found in well-known config")
        return endpoint
