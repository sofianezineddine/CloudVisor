"""
Property-based tests for Keep proxy header injection.

**Validates: Requirements 2.4, 2.7**

Property 3: Proxy Header Injection
For any authenticated request proxied to the Keep service, the API gateway SHALL
inject the `X-Tenant-ID` header with the value of the JWT's `org_id` claim, and
SHALL propagate the `X-Correlation-ID` header (generating one if absent) to the
upstream request.
"""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.core.auth import AuthenticatedUser
from app.core.proxy import correlation_id_var


# ─── Strategies ───────────────────────────────────────────────────────────────

# Generate realistic organization IDs (UUID-like or prefixed strings)
org_id_strategy = st.one_of(
    st.from_regex(r"org_[a-z0-9]{8,24}", fullmatch=True),
    st.uuids().map(str),
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="_-"),
        min_size=3,
        max_size=36,
    ).filter(lambda s: len(s.strip()) > 0),
)

# Generate correlation IDs (UUID format or custom prefixed)
correlation_id_strategy = st.one_of(
    st.uuids().map(str),
    st.from_regex(r"cid_[a-f0-9]{16}", fullmatch=True),
    st.from_regex(r"req_[a-f0-9]{12}", fullmatch=True),
)

# Generate user IDs
user_id_strategy = st.one_of(
    st.uuids().map(str),
    st.from_regex(r"user_[a-z0-9]{8,16}", fullmatch=True),
)

# Generate valid proxy paths (simple, short paths for efficiency)
path_strategy = st.from_regex(r"[a-z][a-z0-9]{0,10}", fullmatch=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_jwt(org_id: str, user_id: str = "user_test123") -> str:
    """Create a minimal JWT token with the given org_id claim."""
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id, "org_id": org_id, "role": "admin"}).encode()
    ).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"fakesignature").rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


def _mock_auth_user(org_id: str, user_id: str = "user_test123") -> AuthenticatedUser:
    """Create a mock AuthenticatedUser with the given org_id."""
    payload = {"sub": user_id, "org_id": org_id, "role": "admin"}
    token = _make_jwt(org_id, user_id)
    return AuthenticatedUser(payload, token)


def _make_mock_request(
    path: str,
    method: str = "GET",
    headers: dict | None = None,
    body: bytes = b"",
) -> MagicMock:
    """Create a mock FastAPI Request object."""
    mock_request = MagicMock()
    mock_request.method = method
    mock_request.headers = headers or {}

    # Mock URL
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url

    # Mock body as async
    async def _body():
        return body

    mock_request.body = _body
    return mock_request


# ─── Property Tests ───────────────────────────────────────────────────────────


class TestProxyHeaderInjection:
    """
    Property 3: Proxy Header Injection

    For any authenticated request proxied to the Keep service, the API gateway
    SHALL inject the X-Tenant-ID header with the value of the JWT's org_id claim,
    and SHALL propagate the X-Correlation-ID header (generating one if absent)
    to the upstream request.

    **Validates: Requirements 2.4, 2.7**
    """

    @given(
        org_id=org_id_strategy,
        user_id=user_id_strategy,
        path=path_strategy,
    )
    @settings(max_examples=100, deadline=30000)
    def test_x_tenant_id_injected_from_org_id(self, org_id: str, user_id: str, path: str):
        """
        Property: For any authenticated request, X-Tenant-ID header is always
        injected with the value of the JWT's org_id claim.

        **Validates: Requirements 2.4**
        """
        assume(len(org_id.strip()) > 0)

        captured_headers = {}

        async def _run():
            from app.api.v1.keep import keep_proxy

            async def mock_request_fn(*args, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                return httpx.Response(
                    status_code=200,
                    content=b'{"ok": true}',
                    headers={"content-type": "application/json"},
                )

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=mock_request_fn)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            user = _mock_auth_user(org_id, user_id)
            request = _make_mock_request(path, headers={"authorization": f"Bearer {_make_jwt(org_id)}"})

            # Set correlation ID context var (simulating middleware)
            correlation_id_var.set(f"cid_test1234567890ab")

            with patch("httpx.AsyncClient", return_value=mock_client):
                response = await keep_proxy(path=path, request=request, user=user)

            return captured_headers

        result_headers = asyncio.run(_run())

        # Verify X-Tenant-ID was injected with the org_id value
        assert "X-Tenant-ID" in result_headers, (
            f"X-Tenant-ID header not found in forwarded headers: "
            f"{list(result_headers.keys())}"
        )
        assert result_headers["X-Tenant-ID"] == org_id, (
            f"X-Tenant-ID mismatch: expected '{org_id}', "
            f"got '{result_headers['X-Tenant-ID']}'"
        )

    @given(
        org_id=org_id_strategy,
        correlation_id=correlation_id_strategy,
        path=path_strategy,
    )
    @settings(max_examples=100, deadline=30000)
    def test_x_correlation_id_propagated_when_present(
        self, org_id: str, correlation_id: str, path: str
    ):
        """
        Property: When X-Correlation-ID is present in the incoming request,
        the proxy includes a correlation ID in the upstream request.

        **Validates: Requirements 2.7**
        """
        assume(len(org_id.strip()) > 0)

        captured_headers = {}

        async def _run():
            from app.api.v1.keep import keep_proxy

            async def mock_request_fn(*args, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                return httpx.Response(
                    status_code=200,
                    content=b'{"ok": true}',
                    headers={"content-type": "application/json"},
                )

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=mock_request_fn)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            user = _mock_auth_user(org_id)
            request = _make_mock_request(
                path,
                headers={
                    "authorization": f"Bearer {_make_jwt(org_id)}",
                    "x-correlation-id": correlation_id,
                },
            )

            # Set correlation ID context var (simulating middleware propagation)
            correlation_id_var.set(correlation_id)

            with patch("httpx.AsyncClient", return_value=mock_client):
                response = await keep_proxy(path=path, request=request, user=user)

            return captured_headers

        result_headers = asyncio.run(_run())

        # Verify X-Correlation-ID is present in forwarded headers
        assert "X-Correlation-ID" in result_headers, (
            "X-Correlation-ID header not found in forwarded headers"
        )
        # The correlation ID should be non-empty
        assert len(result_headers["X-Correlation-ID"]) > 0, (
            "X-Correlation-ID should not be empty"
        )

    @given(
        org_id=org_id_strategy,
        path=path_strategy,
    )
    @settings(max_examples=100, deadline=30000)
    def test_x_correlation_id_generated_when_absent(self, org_id: str, path: str):
        """
        Property: When X-Correlation-ID is NOT present in the incoming request,
        the proxy generates one and includes it in the upstream request.

        **Validates: Requirements 2.7**
        """
        assume(len(org_id.strip()) > 0)

        captured_headers = {}

        async def _run():
            from app.api.v1.keep import keep_proxy

            async def mock_request_fn(*args, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                return httpx.Response(
                    status_code=200,
                    content=b'{"ok": true}',
                    headers={"content-type": "application/json"},
                )

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=mock_request_fn)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            user = _mock_auth_user(org_id)
            # No X-Correlation-ID in request headers
            request = _make_mock_request(
                path,
                headers={"authorization": f"Bearer {_make_jwt(org_id)}"},
            )

            # Clear correlation ID context var to simulate no incoming correlation ID
            correlation_id_var.set("")

            with patch("httpx.AsyncClient", return_value=mock_client):
                response = await keep_proxy(path=path, request=request, user=user)

            return captured_headers

        result_headers = asyncio.run(_run())

        # Verify X-Correlation-ID was generated and included
        assert "X-Correlation-ID" in result_headers, (
            "X-Correlation-ID header should be generated when absent"
        )
        generated_cid = result_headers["X-Correlation-ID"]
        assert len(generated_cid) > 0, (
            "Generated X-Correlation-ID should not be empty"
        )

    @given(
        org_id=org_id_strategy,
        user_id=user_id_strategy,
        path=path_strategy,
    )
    @settings(max_examples=100, deadline=30000)
    def test_both_headers_present_simultaneously(self, org_id: str, user_id: str, path: str):
        """
        Property: For any authenticated request, BOTH X-Tenant-ID and
        X-Correlation-ID are always present in the forwarded request headers.

        **Validates: Requirements 2.4, 2.7**
        """
        assume(len(org_id.strip()) > 0)

        captured_headers = {}

        async def _run():
            from app.api.v1.keep import keep_proxy

            async def mock_request_fn(*args, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                return httpx.Response(
                    status_code=200,
                    content=b'{"ok": true}',
                    headers={"content-type": "application/json"},
                )

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=mock_request_fn)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            user = _mock_auth_user(org_id, user_id)
            request = _make_mock_request(
                path,
                headers={"authorization": f"Bearer {_make_jwt(org_id, user_id)}"},
            )

            # Set a correlation ID (simulating middleware)
            correlation_id_var.set(f"cid_abcdef1234567890")

            with patch("httpx.AsyncClient", return_value=mock_client):
                response = await keep_proxy(path=path, request=request, user=user)

            return captured_headers

        result_headers = asyncio.run(_run())

        # Both headers must be present
        assert "X-Tenant-ID" in result_headers, (
            "X-Tenant-ID must always be present in forwarded headers"
        )
        assert "X-Correlation-ID" in result_headers, (
            "X-Correlation-ID must always be present in forwarded headers"
        )

        # X-Tenant-ID must match org_id exactly
        assert result_headers["X-Tenant-ID"] == org_id

        # X-Correlation-ID must be non-empty
        assert len(result_headers["X-Correlation-ID"]) > 0
