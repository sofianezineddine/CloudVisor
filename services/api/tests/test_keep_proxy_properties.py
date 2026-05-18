"""
Property-based tests for the Keep AIOps API gateway proxy route.

**Validates: Requirements 2.1, 2.2, 2.5**

Property 1: Proxy Request Preservation
- For any HTTP method, path, headers, query params, and body,
  the proxy forwards them unchanged to the Keep service.

Uses pytest + hypothesis for property-based testing.
Patches httpx.AsyncClient in the keep module to capture upstream requests.
"""

import pytest
from unittest.mock import patch, AsyncMock
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from hypothesis import given, settings as h_settings, HealthCheck
from hypothesis import strategies as st
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from main import create_app


# ─── Hypothesis Strategies ────────────────────────────────────────────────────

# Valid HTTP methods supported by the Keep proxy route
http_methods = st.sampled_from(["GET", "POST", "PUT", "PATCH", "DELETE"])

# Valid path segments (alphanumeric + hyphens + underscores, non-empty)
path_segment = st.from_regex(r"[a-zA-Z0-9_\-]{1,30}", fullmatch=True)

# Generate paths like "alerts", "incidents/123", "workflows/abc/executions"
keep_paths = st.lists(path_segment, min_size=1, max_size=4).map("/".join)

# Custom header names (X-Custom-* to avoid conflicts with standard/hop-by-hop headers)
header_name = st.from_regex(r"X-Custom-[A-Za-z]{1,20}", fullmatch=True)

# Header values: printable ASCII without control characters
header_value = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1,
    max_size=100,
)

# Generate a dict of custom headers (0 to 5 headers)
custom_headers = st.dictionaries(header_name, header_value, min_size=0, max_size=5)

# Query parameter keys: valid identifier-like strings
query_key = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,20}", fullmatch=True)

# Query parameter values: URL-safe characters
query_value = st.text(
    alphabet=st.characters(
        min_codepoint=48, max_codepoint=122,
        blacklist_characters="&#?={}[]|\\^`",
    ),
    min_size=1,
    max_size=50,
)

# Generate query parameters (0 to 5 params)
query_params = st.dictionaries(query_key, query_value, min_size=0, max_size=5)

# Request body: either empty or some bytes
request_body = st.one_of(
    st.just(b""),
    st.binary(min_size=1, max_size=500),
)


# ─── Shared App Instance ─────────────────────────────────────────────────────

# Create app once and reuse across hypothesis examples for performance
_app = create_app()
_mock_user = AuthenticatedUser(
    {"sub": "user_test", "org_id": "org_test_123", "role": "admin", "session_id": "sess_test"},
    "test_jwt_token",
)
_app.dependency_overrides[get_current_user] = lambda: _mock_user


# ─── Property Test ────────────────────────────────────────────────────────────

@h_settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    deadline=None,
)
@given(
    method=http_methods,
    path=keep_paths,
    headers=custom_headers,
    params=query_params,
    body=request_body,
)
def test_proxy_request_preservation(method, path, headers, params, body):
    """
    **Validates: Requirements 2.1, 2.2, 2.5**

    Property 1: Proxy Request Preservation

    For any HTTP method, path, headers, query parameters, and body,
    the proxy forwards them unchanged to the Keep service.

    We patch httpx.AsyncClient in the keep module to capture what the proxy
    sends upstream and verify it matches the original request data.
    """
    # Storage for captured upstream request kwargs
    captured = {}

    async def mock_request(**kwargs):
        """Capture the upstream request details (called with keyword args)."""
        captured.update(kwargs)
        return httpx.Response(
            status_code=200,
            content=b'{"ok": true}',
            headers={"content-type": "application/json"},
        )

    # Create a mock AsyncClient context manager
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=mock_request)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
        client = TestClient(_app, raise_server_exceptions=False)

        # Build the request URL with query params
        url = f"/v1/keep/{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        # Send the request through the proxy
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            content=body if body else None,
        )

    # Verify the proxy made an upstream call
    assert "method" in captured, (
        f"No upstream request was captured. Response status: {response.status_code}, "
        f"body: {response.text[:200]}"
    )

    # ── Assertion 1: HTTP method is preserved ─────────────────────────────
    assert captured["method"] == method, (
        f"Method not preserved: sent '{method}', "
        f"proxy forwarded '{captured['method']}'"
    )

    # ── Assertion 2: Path is preserved ────────────────────────────────────
    upstream_url = captured["url"]
    parsed_upstream = urlparse(upstream_url)
    # The proxy builds: {keep_service_url}/{path} → http://cv-keep:8007/{path}
    expected_path = f"/{path}"
    assert parsed_upstream.path == expected_path, (
        f"Path not preserved: expected '{expected_path}', "
        f"got '{parsed_upstream.path}' in URL '{upstream_url}'"
    )

    # ── Assertion 3: Query parameters are preserved ───────────────────────
    if params:
        upstream_params = parse_qs(parsed_upstream.query)
        for key, value in params.items():
            assert key in upstream_params, (
                f"Query param '{key}' not forwarded. "
                f"Upstream query: '{parsed_upstream.query}'"
            )
            assert value in upstream_params[key], (
                f"Query param '{key}' value mismatch: "
                f"expected '{value}', got '{upstream_params[key]}'"
            )

    # ── Assertion 4: Custom headers are preserved ─────────────────────────
    upstream_headers = captured.get("headers", {})
    upstream_headers_lower = {k.lower(): v for k, v in upstream_headers.items()}
    for h_name, h_value in headers.items():
        assert h_name.lower() in upstream_headers_lower, (
            f"Header '{h_name}' not forwarded to upstream. "
            f"Upstream headers: {list(upstream_headers.keys())}"
        )
        assert upstream_headers_lower[h_name.lower()] == h_value, (
            f"Header '{h_name}' value mismatch: "
            f"expected '{h_value}', got '{upstream_headers_lower[h_name.lower()]}'"
        )

    # ── Assertion 5: Request body is preserved ────────────────────────────
    upstream_body = captured.get("content")
    if body:
        assert upstream_body == body, (
            f"Body not preserved: sent {len(body)} bytes, "
            f"got {len(upstream_body) if upstream_body else 0} bytes upstream"
        )
    else:
        # Empty body: upstream should have None or empty content
        assert upstream_body is None or upstream_body == b"", (
            f"Expected empty body upstream, got: {upstream_body!r}"
        )
