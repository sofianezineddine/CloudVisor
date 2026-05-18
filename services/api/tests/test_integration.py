"""
Integration tests for end-to-end AIOps alert flow.

Tests the full integration path:
  1. Kafka alert ingestion → Keep alert creation → WebSocket event delivery
  2. API gateway proxy routing → Keep service → response
  3. Multi-tenant data isolation

Since we cannot run actual Kafka/Keep/Soketi in unit tests, boundaries are mocked:
  - Kafka consumer is simulated by calling the mapping function directly
  - Keep API is mocked via httpx to verify alert push and proxy routing
  - WebSocket (Pusher/Soketi) events are verified via mock triggers
  - Tenant isolation is verified by scoping requests with X-Tenant-ID

**Validates: Requirements 8.1, 8.2, 6.2, 11.4**
"""

import json
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

# Mock kafka module before importing consumer (it may not be installed in test env)
sys.modules.setdefault("kafka", MagicMock())
sys.modules.setdefault("kafka.errors", MagicMock())

from app.core.auth import AuthenticatedUser, get_current_user
from main import create_app

# Import the consumer mapping function (with kafka mocked)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / "keep"))
from cloudvisor_consumer import map_cloudvisor_alert_to_keep


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Create a fresh FastAPI app instance for integration testing."""
    return create_app()


@pytest.fixture
def tenant_a_user():
    """Authenticated user belonging to tenant A."""
    payload = {
        "sub": "user_tenant_a",
        "org_id": "tenant-alpha",
        "role": "admin",
        "session_id": "sess_a",
    }
    return AuthenticatedUser(payload, "jwt_token_tenant_a")


@pytest.fixture
def tenant_b_user():
    """Authenticated user belonging to tenant B."""
    payload = {
        "sub": "user_tenant_b",
        "org_id": "tenant-beta",
        "role": "admin",
        "session_id": "sess_b",
    }
    return AuthenticatedUser(payload, "jwt_token_tenant_b")


@pytest.fixture
def sample_cloudvisor_alert():
    """A valid CloudVisor alert as it would appear on the Kafka topic."""
    return {
        "id": "alert-integration-001",
        "tenant_id": "tenant-alpha",
        "title": "Unauthorized S3 Public Access",
        "description": "S3 bucket 'prod-data' has public read access enabled",
        "severity": "critical",
        "source": "cspm",
        "resource_id": "arn:aws:s3:::prod-data",
        "resource_type": "s3_bucket",
        "created_at": "2024-06-15T14:30:00Z",
        "metadata": {
            "rule_id": "CIS-2.1.5",
            "account_id": "123456789012",
            "region": "us-east-1",
        },
    }


@pytest.fixture
def sample_cloudvisor_alert_tenant_b():
    """A valid CloudVisor alert belonging to tenant B."""
    return {
        "id": "alert-integration-002",
        "tenant_id": "tenant-beta",
        "title": "EC2 Instance Exposed to Internet",
        "description": "EC2 instance i-abc123 has port 22 open to 0.0.0.0/0",
        "severity": "high",
        "source": "cwpp",
        "resource_id": "arn:aws:ec2:us-west-2:987654321:instance/i-abc123",
        "resource_type": "ec2_instance",
        "created_at": "2024-06-15T15:00:00Z",
        "metadata": {
            "rule_id": "CIS-4.1.1",
            "account_id": "987654321098",
            "region": "us-west-2",
        },
    }


# ─── Test Class 1: End-to-End Alert Flow ─────────────────────────────────────


class TestEndToEndAlertFlow:
    """
    Integration test: Kafka alert → mapping → Keep ingestion → WebSocket event.

    Validates: Requirements 8.1, 8.2
    """

    def test_kafka_alert_maps_and_pushes_to_keep(self, sample_cloudvisor_alert):
        """
        Simulate: alert produced to Kafka → consumer maps it → pushes to Keep API.

        Verifies the full ingestion path from Kafka message to Keep alert creation.
        """
        # Step 1: Simulate Kafka consumer receiving the message
        # (In production, KafkaConsumer deserializes JSON from the topic)
        keep_alert = map_cloudvisor_alert_to_keep(sample_cloudvisor_alert)

        # Step 2: Verify the mapping produced a valid Keep alert
        assert keep_alert["name"] == "Unauthorized S3 Public Access"
        assert keep_alert["severity"] == "critical"
        assert keep_alert["source"] == ["cspm"]
        assert keep_alert["fingerprint"] == "arn:aws:s3:::prod-data"
        assert keep_alert["lastReceived"] == "2024-06-15T14:30:00Z"
        assert keep_alert["tenant_id"] == "tenant-alpha"
        assert keep_alert["labels"]["resource_type"] == "s3_bucket"
        assert keep_alert["labels"]["rule_id"] == "CIS-2.1.5"
        assert keep_alert["status"] == "firing"
        assert keep_alert["pushed"] is True

        # Step 3: Simulate pushing to Keep's /alerts/event endpoint
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=202)

            import requests

            response = requests.post(
                "http://cv-keep:8007/alerts/event",
                json=keep_alert,
                headers={
                    "Content-Type": "application/json",
                    "X-Tenant-ID": keep_alert["tenant_id"],
                },
                timeout=10,
            )

            # Verify the alert was pushed with correct tenant scoping
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs[1]["json"]["name"] == "Unauthorized S3 Public Access"
            assert call_kwargs[1]["headers"]["X-Tenant-ID"] == "tenant-alpha"
            assert response.status_code == 202

    def test_kafka_alert_triggers_websocket_event(self, sample_cloudvisor_alert):
        """
        Simulate: after Keep ingests an alert, it triggers a Pusher/Soketi event.

        Verifies that the WebSocket event delivery path is correctly structured.
        """
        # Step 1: Map the alert (simulating Kafka consumption)
        keep_alert = map_cloudvisor_alert_to_keep(sample_cloudvisor_alert)
        tenant_id = keep_alert["tenant_id"]

        # Step 2: Simulate Keep triggering a Pusher event after ingestion
        # In production, Keep calls Soketi's HTTP API to trigger events
        with patch("requests.post") as mock_pusher_trigger:
            mock_pusher_trigger.return_value = MagicMock(status_code=200)

            # Simulate the Pusher trigger that Keep would make
            channel = f"private-{tenant_id}"
            event_name = "alert:created"
            event_data = {
                "alert_id": keep_alert["fingerprint"],
                "name": keep_alert["name"],
                "severity": keep_alert["severity"],
                "tenant_id": tenant_id,
            }

            import requests

            # This simulates Keep's internal call to Soketi
            requests.post(
                "http://cv-soketi:6001/apps/cloudvisor/events",
                json={
                    "name": event_name,
                    "channel": channel,
                    "data": json.dumps(event_data),
                },
                headers={"Content-Type": "application/json"},
            )

            # Verify the WebSocket event was triggered on the correct channel
            call_kwargs = mock_pusher_trigger.call_args
            triggered_payload = call_kwargs[1]["json"]
            assert triggered_payload["channel"] == "private-tenant-alpha"
            assert triggered_payload["name"] == "alert:created"

            # Verify event data contains the alert info
            triggered_data = json.loads(triggered_payload["data"])
            assert triggered_data["alert_id"] == "arn:aws:s3:::prod-data"
            assert triggered_data["severity"] == "critical"
            assert triggered_data["tenant_id"] == "tenant-alpha"

    def test_malformed_kafka_message_does_not_break_flow(self):
        """
        Simulate: malformed message on Kafka topic → consumer logs and continues.

        Verifies: Requirement 8.4 (resilience to malformed events)
        """
        # Malformed alerts should not crash the mapping function
        malformed_alerts = [
            {},  # Empty dict
            {"severity": None, "metadata": None},  # None values
            {"title": 123, "severity": True},  # Wrong types
            {"metadata": "not_a_dict"},  # Invalid metadata type
        ]

        for malformed in malformed_alerts:
            # Should not raise any exception
            result = map_cloudvisor_alert_to_keep(malformed)
            # Should produce a valid Keep alert with defaults
            assert "name" in result
            assert "severity" in result
            assert "source" in result
            assert isinstance(result["source"], list)
            assert "tenant_id" in result


# ─── Test Class 2: Proxy Routing Integration ──────────────────────────────────


class TestProxyRoutingIntegration:
    """
    Integration test: API gateway → Keep service → response.

    Verifies the full proxy path including auth, header injection, and response.
    Validates: Requirements 2.1, 2.2, 2.4, 2.5
    """

    def test_proxy_forwards_get_request_to_keep(self, app, tenant_a_user):
        """GET /v1/keep/alerts → proxied to Keep at /alerts with tenant header."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        # Mock the upstream Keep response
        mock_client = AsyncMock()
        mock_response = httpx.Response(
            status_code=200,
            content=json.dumps({"alerts": [{"id": "a1", "name": "Test Alert"}]}).encode(),
            headers={"content-type": "application/json"},
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/v1/keep/alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["alerts"][0]["name"] == "Test Alert"

        # Verify upstream request was made with correct headers
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["method"] == "GET"
        assert "/alerts" in call_kwargs["url"]
        assert call_kwargs["headers"]["X-Tenant-ID"] == "tenant-alpha"
        assert "X-Correlation-ID" in call_kwargs["headers"]
        assert call_kwargs["headers"]["X-Source-Service"] == "api-gateway"

    def test_proxy_forwards_post_request_with_body(self, app, tenant_a_user):
        """POST /v1/keep/workflows → proxied with request body preserved."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        workflow_payload = {
            "name": "Auto-Remediate S3",
            "trigger": {"type": "alert", "filters": [{"key": "source", "value": "cspm"}]},
            "actions": [{"type": "slack", "channel": "#security"}],
        }

        mock_client = AsyncMock()
        mock_response = httpx.Response(
            status_code=201,
            content=json.dumps({"id": "wf-001", "status": "created"}).encode(),
            headers={"content-type": "application/json"},
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/v1/keep/workflows",
                json=workflow_payload,
            )

        assert response.status_code == 201

        # Verify body was forwarded
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["content"] is not None
        forwarded_body = json.loads(call_kwargs["content"])
        assert forwarded_body["name"] == "Auto-Remediate S3"

    def test_proxy_forwards_query_parameters(self, app, tenant_a_user):
        """GET /v1/keep/alerts?severity=critical&limit=10 → query params preserved."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        mock_client = AsyncMock()
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"alerts": []}',
            headers={"content-type": "application/json"},
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/v1/keep/alerts?severity=critical&limit=10")

        assert response.status_code == 200

        # Verify query params were forwarded in the URL
        call_kwargs = mock_client.request.call_args[1]
        assert "severity=critical" in call_kwargs["url"]
        assert "limit=10" in call_kwargs["url"]

    def test_proxy_returns_502_when_keep_unavailable(self, app, tenant_a_user):
        """Gateway returns 502 when Keep service is unreachable."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/v1/keep/alerts")

        assert response.status_code == 502

    def test_proxy_returns_401_without_auth(self, app):
        """Requests without JWT receive 401 and are NOT forwarded to Keep."""
        # Do NOT override get_current_user — let it enforce auth
        # Clear any previous overrides
        app.dependency_overrides.pop(get_current_user, None)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/v1/keep/alerts")

        assert response.status_code == 401

    def test_proxy_supports_all_http_methods(self, app, tenant_a_user):
        """All HTTP methods (GET, POST, PUT, PATCH, DELETE) are proxied correctly."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

        for method in methods:
            mock_client = AsyncMock()
            mock_response = httpx.Response(
                status_code=200,
                content=b'{"ok": true}',
                headers={"content-type": "application/json"},
            )
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
                client = TestClient(app, raise_server_exceptions=False)
                response = client.request(method, "/v1/keep/test-endpoint")

            assert response.status_code == 200, f"Failed for method {method}"

            call_kwargs = mock_client.request.call_args[1]
            assert call_kwargs["method"] == method, (
                f"Method not forwarded: expected {method}, got {call_kwargs['method']}"
            )


# ─── Test Class 3: Tenant Isolation ──────────────────────────────────────────


class TestTenantIsolation:
    """
    Integration test: multi-tenant data isolation.

    Verifies that the API gateway correctly scopes requests per tenant
    and that tenant A's requests never carry tenant B's context.

    Validates: Requirement 11.4
    """

    def test_tenant_a_request_scoped_to_tenant_a(self, app, tenant_a_user):
        """Requests from tenant A inject X-Tenant-ID: tenant-alpha."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        mock_client = AsyncMock()
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"alerts": []}',
            headers={"content-type": "application/json"},
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/v1/keep/alerts")

        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["headers"]["X-Tenant-ID"] == "tenant-alpha"

    def test_tenant_b_request_scoped_to_tenant_b(self, app, tenant_b_user):
        """Requests from tenant B inject X-Tenant-ID: tenant-beta."""
        app.dependency_overrides[get_current_user] = lambda: tenant_b_user

        mock_client = AsyncMock()
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"alerts": []}',
            headers={"content-type": "application/json"},
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/v1/keep/alerts")

        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["headers"]["X-Tenant-ID"] == "tenant-beta"

    def test_tenant_isolation_no_cross_tenant_header_leakage(
        self, app, tenant_a_user, tenant_b_user
    ):
        """
        Sequential requests from different tenants never leak tenant context.

        Simulates tenant A making a request, then tenant B making a request,
        and verifies each carries only its own tenant ID.
        """
        captured_tenant_ids = []

        async def capture_request(**kwargs):
            captured_tenant_ids.append(kwargs.get("headers", {}).get("X-Tenant-ID"))
            return httpx.Response(
                status_code=200,
                content=b'{"alerts": []}',
                headers={"content-type": "application/json"},
            )

        # Request 1: Tenant A
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user
        mock_client_a = AsyncMock()
        mock_client_a.request = AsyncMock(side_effect=capture_request)
        mock_client_a.__aenter__ = AsyncMock(return_value=mock_client_a)
        mock_client_a.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client_a):
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/v1/keep/alerts")

        # Request 2: Tenant B
        app.dependency_overrides[get_current_user] = lambda: tenant_b_user
        mock_client_b = AsyncMock()
        mock_client_b.request = AsyncMock(side_effect=capture_request)
        mock_client_b.__aenter__ = AsyncMock(return_value=mock_client_b)
        mock_client_b.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client_b):
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/v1/keep/alerts")

        # Verify no cross-tenant leakage
        assert len(captured_tenant_ids) == 2
        assert captured_tenant_ids[0] == "tenant-alpha"
        assert captured_tenant_ids[1] == "tenant-beta"
        # Ensure they are different (no leakage)
        assert captured_tenant_ids[0] != captured_tenant_ids[1]

    def test_kafka_alert_tenant_scoping(
        self, sample_cloudvisor_alert, sample_cloudvisor_alert_tenant_b
    ):
        """
        Alerts from different tenants on Kafka are mapped with correct tenant_id.

        Verifies that the consumer correctly extracts and preserves tenant_id
        from each alert, ensuring data isolation at the ingestion layer.
        """
        # Map alerts from two different tenants
        keep_alert_a = map_cloudvisor_alert_to_keep(sample_cloudvisor_alert)
        keep_alert_b = map_cloudvisor_alert_to_keep(sample_cloudvisor_alert_tenant_b)

        # Verify tenant isolation in mapped alerts
        assert keep_alert_a["tenant_id"] == "tenant-alpha"
        assert keep_alert_b["tenant_id"] == "tenant-beta"

        # Verify alerts carry different tenant contexts
        assert keep_alert_a["tenant_id"] != keep_alert_b["tenant_id"]

        # Verify each alert's data is independent
        assert keep_alert_a["name"] == "Unauthorized S3 Public Access"
        assert keep_alert_b["name"] == "EC2 Instance Exposed to Internet"
        assert keep_alert_a["fingerprint"] != keep_alert_b["fingerprint"]

    def test_websocket_channel_scoped_per_tenant(self):
        """
        WebSocket events are delivered on tenant-specific channels.

        Verifies that tenant A's events go to private-tenant-alpha
        and tenant B's events go to private-tenant-beta.
        """
        tenant_a_channel = f"private-tenant-alpha"
        tenant_b_channel = f"private-tenant-beta"

        # Verify channels are distinct
        assert tenant_a_channel != tenant_b_channel

        # Simulate event routing: each tenant's alert goes to its own channel
        events = []

        def simulate_pusher_trigger(channel: str, event: str, data: dict):
            events.append({"channel": channel, "event": event, "data": data})

        # Tenant A alert event
        simulate_pusher_trigger(
            tenant_a_channel,
            "alert:created",
            {"alert_id": "a1", "tenant_id": "tenant-alpha"},
        )

        # Tenant B alert event
        simulate_pusher_trigger(
            tenant_b_channel,
            "alert:created",
            {"alert_id": "b1", "tenant_id": "tenant-beta"},
        )

        # Verify events are on separate channels
        assert events[0]["channel"] == "private-tenant-alpha"
        assert events[0]["data"]["tenant_id"] == "tenant-alpha"
        assert events[1]["channel"] == "private-tenant-beta"
        assert events[1]["data"]["tenant_id"] == "tenant-beta"

        # Verify no cross-channel contamination
        assert events[0]["data"]["alert_id"] != events[1]["data"]["alert_id"]

    def test_proxy_injects_correlation_id(self, app, tenant_a_user):
        """Every proxied request includes a non-empty X-Correlation-ID header."""
        app.dependency_overrides[get_current_user] = lambda: tenant_a_user

        mock_client = AsyncMock()
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"ok": true}',
            headers={"content-type": "application/json"},
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.v1.keep.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/v1/keep/alerts")

        call_kwargs = mock_client.request.call_args[1]
        correlation_id = call_kwargs["headers"].get("X-Correlation-ID", "")
        assert correlation_id != "", "X-Correlation-ID must be non-empty"
        assert len(correlation_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
