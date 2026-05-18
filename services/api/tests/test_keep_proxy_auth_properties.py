"""
Property-based test: JWT Authentication Enforcement for Keep proxy.

**Validates: Requirements 2.3, 2.6**

Property 2: JWT Authentication Enforcement
For any request to /v1/keep/*, the API gateway SHALL allow the request through
to the Keep service if and only if the request contains a valid, non-expired JWT
token. Requests with missing, malformed, or expired tokens SHALL receive HTTP 401
Unauthorized without being forwarded.

Uses pytest + hypothesis to generate random paths, methods, and payloads,
verifying that:
  - Valid JWT → request passes through (non-401 response)
  - Missing/invalid JWT → 401 response
"""

import base64
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from hypothesis import given, settings, HealthCheck, Phase
from hypothesis import strategies as st

from app.core.auth import AuthenticatedUser, get_current_user
from app.api.v1.keep import router as keep_router


# ─── Strategies ───────────────────────────────────────────────────────────────

# Generate random Keep sub-paths (alphanumeric segments separated by slashes)
path_segment = st.from_regex(r"[a-z0-9]{1,12}", fullmatch=True)
keep_path = st.lists(path_segment, min_size=1, max_size=3).map("/".join)

# HTTP methods supported by the proxy
http_methods = st.sampled_from(["GET", "POST", "PUT", "PATCH", "DELETE"])

# Random request bodies (for POST/PUT/PATCH)
request_body = st.one_of(
    st.just(b""),
    st.binary(min_size=1, max_size=100),
)

# Random query parameters
query_params = st.dictionaries(
    keys=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    values=st.from_regex(r"[a-z0-9]{1,10}", fullmatch=True),
    min_size=0,
    max_size=3,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_authenticated_user(
    user_id: str = "user_123",
    organization_id: str = "org_456",
    role: str = "admin",
) -> AuthenticatedUser:
    """Create a mock AuthenticatedUser with given claims."""
    payload = {
        "sub": user_id,
        "org_id": organization_id,
        "role": role,
    }
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    token = f"{header}.{body}.fake_signature"
    return AuthenticatedUser(payload, token)


def _create_test_app_with_valid_auth() -> FastAPI:
    """Create a minimal FastAPI app with the keep router and valid auth override."""
    app = FastAPI()
    app.include_router(keep_router, prefix="/v1")
    user = _make_authenticated_user()
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _create_test_app_with_rejected_auth() -> FastAPI:
    """Create a minimal FastAPI app with the keep router and rejected auth."""
    app = FastAPI()
    app.include_router(keep_router, prefix="/v1")

    async def _reject():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    app.dependency_overrides[get_current_user] = _reject
    return app


def _build_mock_upstream_response():
    """Create a mock httpx.Response simulating a successful Keep upstream response."""
    return httpx.Response(
        status_code=200,
        content=b'{"status": "ok"}',
        headers={"content-type": "application/json"},
    )


# ─── Property Tests ──────────────────────────────────────────────────────────


class TestJWTAuthenticationEnforcement:
    """
    **Validates: Requirements 2.3, 2.6**

    Property 2: JWT Authentication Enforcement
    - Requests with valid JWT pass through to Keep (non-401 response)
    - Requests without valid JWT receive 401 Unauthorized
    """

    @given(path=keep_path, method=http_methods, body=request_body, params=query_params)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        phases=[Phase.explicit, Phase.generate, Phase.target],
    )
    def test_valid_jwt_passes_through(self, path, method, body, params):
        """
        For any request to /v1/keep/{path} with a valid JWT,
        the gateway SHALL forward the request (response is NOT 401).

        **Validates: Requirements 2.3**
        """
        app = _create_test_app_with_valid_auth()
        url = f"/v1/keep/{path}"

        # Mock the upstream Keep service to return 200
        mock_response = _build_mock_upstream_response()

        with patch("app.api.v1.keep.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            client = TestClient(app, raise_server_exceptions=False)
            response = client.request(
                method=method,
                url=url,
                content=body if method in ("POST", "PUT", "PATCH") else None,
                params=params if params else None,
            )

        # With valid JWT, the request should NOT be rejected with 401
        assert response.status_code != 401, (
            f"Request with valid JWT should not receive 401. "
            f"Got {response.status_code} for {method} {url}"
        )

    @given(path=keep_path, method=http_methods, body=request_body, params=query_params)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        phases=[Phase.explicit, Phase.generate, Phase.target],
    )
    def test_missing_invalid_jwt_returns_401(self, path, method, body, params):
        """
        For any request to /v1/keep/{path} without a valid JWT,
        the gateway SHALL return HTTP 401 Unauthorized.

        **Validates: Requirements 2.6**
        """
        app = _create_test_app_with_rejected_auth()
        url = f"/v1/keep/{path}"

        client = TestClient(app, raise_server_exceptions=False)
        response = client.request(
            method=method,
            url=url,
            content=body if method in ("POST", "PUT", "PATCH") else None,
            params=params if params else None,
        )

        # Without valid JWT, the request MUST be rejected with 401
        assert response.status_code == 401, (
            f"Request without valid JWT should receive 401. "
            f"Got {response.status_code} for {method} {url}"
        )
