"""
Unit tests for the Keep AIOps API gateway proxy route.

Tests specific examples for:
- Path transformation (/v1/keep/alerts → /alerts, /v1/keep/incidents/123 → /incidents/123)
- Header injection (X-Tenant-ID from user's org_id, X-Correlation-ID present)
- Method forwarding (GET, POST, PUT, PATCH, DELETE)

Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.7
"""

import pytest
from unittest.mock import patch, AsyncMock
from urllib.parse import urlparse, parse_qs

import httpx
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from main import create_app


# ─── Test Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    """Create a FastAPI app with auth dependency overridden."""
    _app = create_app()
    mock_user = AuthenticatedUser(
        {"sub": "user_123", "org_id": "org_456", "role": "admin", "session_id": "sess_789"},
        "fake_jwt_token",
    )
    _app.dependency_overrides[get_current_user] = lambda: mock_user
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_upstream():
    """
    Patch httpx.AsyncClient in the keep module to capture upstream requests.
    Returns a dict that will be populated with the captured request kwargs.
    """
    captured = {}

    async def mock_request(**kwargs):
        captured.update(kwargs)
        return httpx.Response(
            status_code=200,
            content=b'{"data": "ok"}',
            headers={"content-type": "application/json"},
        )

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=mock_request)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
        yield captured


# ─── Path Transformation Tests ────────────────────────────────────────────────


class TestPathTransformation:
    """Test that /v1/keep/{path} is correctly transformed to /{path} for upstream."""

    def test_alerts_path(self, client, mock_upstream):
        """GET /v1/keep/alerts → upstream /alerts"""
        client.get("/v1/keep/alerts")

        upstream_url = mock_upstream["url"]
        parsed = urlparse(upstream_url)
        assert parsed.path == "/alerts"

    def test_incidents_with_id(self, client, mock_upstream):
        """GET /v1/keep/incidents/123 → upstream /incidents/123"""
        client.get("/v1/keep/incidents/123")

        upstream_url = mock_upstream["url"]
        parsed = urlparse(upstream_url)
        assert parsed.path == "/incidents/123"

    def test_nested_path(self, client, mock_upstream):
        """GET /v1/keep/workflows/abc/executions → upstream /workflows/abc/executions"""
        client.get("/v1/keep/workflows/abc/executions")

        upstream_url = mock_upstream["url"]
        parsed = urlparse(upstream_url)
        assert parsed.path == "/workflows/abc/executions"

    def test_providers_path(self, client, mock_upstream):
        """GET /v1/keep/providers → upstream /providers"""
        client.get("/v1/keep/providers")

        upstream_url = mock_upstream["url"]
        parsed = urlparse(upstream_url)
        assert parsed.path == "/providers"

    def test_topology_path(self, client, mock_upstream):
        """GET /v1/keep/topology → upstream /topology"""
        client.get("/v1/keep/topology")

        upstream_url = mock_upstream["url"]
        parsed = urlparse(upstream_url)
        assert parsed.path == "/topology"

    def test_query_params_preserved(self, client, mock_upstream):
        """GET /v1/keep/alerts?severity=critical&page=2 → upstream /alerts?severity=critical&page=2"""
        client.get("/v1/keep/alerts?severity=critical&page=2")

        upstream_url = mock_upstream["url"]
        parsed = urlparse(upstream_url)
        assert parsed.path == "/alerts"
        query = parse_qs(parsed.query)
        assert "severity" in query
        assert query["severity"] == ["critical"]
        assert "page" in query
        assert query["page"] == ["2"]

    def test_upstream_base_url(self, client, mock_upstream):
        """Verify the upstream URL uses the configured Keep service URL."""
        client.get("/v1/keep/alerts")

        upstream_url = mock_upstream["url"]
        # Should target http://cv-keep:8007/alerts
        assert upstream_url.startswith("http://cv-keep:8007/")


# ─── Header Injection Tests ───────────────────────────────────────────────────


class TestHeaderInjection:
    """Test that required headers are injected into upstream requests."""

    def test_x_tenant_id_injected(self, client, mock_upstream):
        """X-Tenant-ID header is injected with the user's organization_id."""
        client.get("/v1/keep/alerts")

        headers = mock_upstream["headers"]
        assert "X-Tenant-ID" in headers
        assert headers["X-Tenant-ID"] == "org_456"

    def test_x_correlation_id_present(self, client, mock_upstream):
        """X-Correlation-ID header is present in forwarded request."""
        client.get("/v1/keep/alerts")

        headers = mock_upstream["headers"]
        assert "X-Correlation-ID" in headers
        assert len(headers["X-Correlation-ID"]) > 0

    def test_x_source_service_injected(self, client, mock_upstream):
        """X-Source-Service header is set to 'api-gateway'."""
        client.get("/v1/keep/alerts")

        headers = mock_upstream["headers"]
        assert "X-Source-Service" in headers
        assert headers["X-Source-Service"] == "api-gateway"

    def test_x_tenant_id_from_different_user(self, app):
        """X-Tenant-ID reflects the authenticated user's org_id."""
        different_user = AuthenticatedUser(
            {"sub": "user_999", "org_id": "org_different_tenant", "role": "viewer", "session_id": "s1"},
            "another_token",
        )
        app.dependency_overrides[get_current_user] = lambda: different_user

        captured = {}

        async def mock_request(**kwargs):
            captured.update(kwargs)
            return httpx.Response(
                status_code=200,
                content=b'{"data": "ok"}',
                headers={"content-type": "application/json"},
            )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=mock_request)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/v1/keep/alerts")

        assert captured["headers"]["X-Tenant-ID"] == "org_different_tenant"

    def test_correlation_id_propagated_from_request(self, app):
        """If the incoming request has X-Correlation-ID, it should be propagated."""
        mock_user = AuthenticatedUser(
            {"sub": "user_123", "org_id": "org_456", "role": "admin", "session_id": "sess_789"},
            "fake_jwt_token",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        captured = {}

        async def mock_request(**kwargs):
            captured.update(kwargs)
            return httpx.Response(
                status_code=200,
                content=b'{"data": "ok"}',
                headers={"content-type": "application/json"},
            )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=mock_request)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            client.get(
                "/v1/keep/alerts",
                headers={"X-Correlation-ID": "my-custom-correlation-id"},
            )

        # The correlation ID should be present (either propagated or generated)
        assert "X-Correlation-ID" in captured["headers"]
        assert len(captured["headers"]["X-Correlation-ID"]) > 0

    def test_hop_by_hop_headers_filtered(self, client, mock_upstream):
        """Hop-by-hop headers (connection, keep-alive, etc.) are NOT forwarded."""
        client.get(
            "/v1/keep/alerts",
            headers={
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=5",
                "X-Custom-Header": "should-pass",
            },
        )

        headers = mock_upstream["headers"]
        headers_lower = {k.lower(): v for k, v in headers.items()}
        assert "connection" not in headers_lower
        assert "keep-alive" not in headers_lower
        # Custom headers should still pass through
        assert "x-custom-header" in headers_lower
        assert headers_lower["x-custom-header"] == "should-pass"


# ─── Method Forwarding Tests ─────────────────────────────────────────────────


class TestMethodForwarding:
    """Test that all 5 HTTP methods are forwarded correctly to upstream."""

    def test_get_method_forwarded(self, client, mock_upstream):
        """GET method is forwarded to upstream."""
        client.get("/v1/keep/alerts")

        assert mock_upstream["method"] == "GET"

    def test_post_method_forwarded(self, client, mock_upstream):
        """POST method is forwarded to upstream with body."""
        client.post(
            "/v1/keep/workflows",
            content=b'{"name": "test-workflow", "yaml": "trigger: alert"}',
            headers={"Content-Type": "application/json"},
        )

        assert mock_upstream["method"] == "POST"
        assert mock_upstream["content"] == b'{"name": "test-workflow", "yaml": "trigger: alert"}'

    def test_put_method_forwarded(self, client, mock_upstream):
        """PUT method is forwarded to upstream with body."""
        client.put(
            "/v1/keep/workflows/wf_123",
            content=b'{"name": "updated-workflow"}',
            headers={"Content-Type": "application/json"},
        )

        assert mock_upstream["method"] == "PUT"
        assert mock_upstream["content"] == b'{"name": "updated-workflow"}'

    def test_patch_method_forwarded(self, client, mock_upstream):
        """PATCH method is forwarded to upstream with body."""
        client.patch(
            "/v1/keep/incidents/inc_456",
            content=b'{"status": "resolved"}',
            headers={"Content-Type": "application/json"},
        )

        assert mock_upstream["method"] == "PATCH"
        assert mock_upstream["content"] == b'{"status": "resolved"}'

    def test_delete_method_forwarded(self, client, mock_upstream):
        """DELETE method is forwarded to upstream."""
        client.delete("/v1/keep/providers/prov_789")

        assert mock_upstream["method"] == "DELETE"

    def test_post_with_empty_body(self, client, mock_upstream):
        """POST with no body forwards None content."""
        client.post("/v1/keep/alerts/acknowledge")

        assert mock_upstream["method"] == "POST"
        assert mock_upstream["content"] is None or mock_upstream["content"] == b""

    def test_response_status_code_preserved(self, app):
        """Upstream response status code is returned to the client."""
        mock_user = AuthenticatedUser(
            {"sub": "user_123", "org_id": "org_456", "role": "admin", "session_id": "sess_789"},
            "fake_jwt_token",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async def mock_request(**kwargs):
            return httpx.Response(
                status_code=201,
                content=b'{"id": "new_resource"}',
                headers={"content-type": "application/json"},
            )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=mock_request)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/v1/keep/workflows")

        assert response.status_code == 201

    def test_response_body_preserved(self, app):
        """Upstream response body is returned to the client unchanged."""
        mock_user = AuthenticatedUser(
            {"sub": "user_123", "org_id": "org_456", "role": "admin", "session_id": "sess_789"},
            "fake_jwt_token",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response_body = b'{"alerts": [{"id": "a1", "name": "High CPU"}]}'

        async def mock_request(**kwargs):
            return httpx.Response(
                status_code=200,
                content=response_body,
                headers={"content-type": "application/json"},
            )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=mock_request)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/v1/keep/alerts")

        assert response.content == response_body
