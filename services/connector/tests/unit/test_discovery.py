"""Unit tests for the cloud discovery service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


def _make_account(provider="aws", account_id="123456789012", org_id="org-abc"):
    account = MagicMock()
    account.id = "acct-uuid-1"
    account.organization_id = org_id
    account.provider = provider
    account.account_id = account_id
    account.region = "us-east-1"
    account.vault_secret_path = None
    account.credentials_enc = {"access_key": "AKIA...", "secret_key": "secret"}
    account.status = "active"
    return account


def _make_resource(cloud_id="arn:aws:ec2:us-east-1:123:instance/i-abc"):
    from cloudvisor_types.models import CloudResource, CloudProvider, Environment
    return CloudResource(
        id="res-uuid-1",
        cloud_resource_id=cloud_id,
        provider=CloudProvider.AWS,
        account_id="123456789012",
        region="us-east-1",
        resource_type="aws::ec2::instance",
        name="my-instance",
        tags={},
        raw={},
        organization_id="org-abc",
        is_public=False,
        environment=Environment.PROD,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )


class TestCloudDiscoveryService:
    @pytest.mark.asyncio
    async def test_get_credentials_from_db_fallback(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        producer = AsyncMock()
        svc = CloudDiscoveryService(account=account, producer=producer)
        creds = await svc._get_credentials()
        assert creds["access_key"] == "AKIA..."

    @pytest.mark.asyncio
    async def test_get_credentials_prefers_vault(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        account.vault_secret_path = "cloudvisor/credentials/acct-uuid-1"
        vault_client = AsyncMock()
        vault_client.retrieve_credentials = AsyncMock(return_value={"access_key": "VAULT_KEY"})
        producer = AsyncMock()
        svc = CloudDiscoveryService(account=account, producer=producer, vault_client=vault_client)
        creds = await svc._get_credentials()
        assert creds["access_key"] == "VAULT_KEY"

    @pytest.mark.asyncio
    async def test_discover_full_emits_events(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        producer = AsyncMock()
        resource = _make_resource()

        with patch("app.services.discovery.ClientFactory") as mock_factory, \
             patch("app.services.discovery.BatchNormalizer") as mock_norm_cls:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.list_resources = AsyncMock(return_value=[{"type": "Instance", "id": "i-abc"}])
            mock_factory.create_client = MagicMock(return_value=mock_client)

            mock_norm = MagicMock()
            mock_norm.normalize_batch = MagicMock(return_value=[resource])
            mock_norm_cls.return_value = mock_norm

            svc = CloudDiscoveryService(account=account, producer=producer)
            result = await svc.discover_full(correlation_id="corr-123")

        assert result.discovered == 1
        producer.emit_resource_discovered.assert_called_once()
        producer.emit_sync_started.assert_called_once()
        producer.emit_sync_finished.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_full_marks_deleted_resources(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        producer = AsyncMock()
        resource = _make_resource("arn:aws:ec2:us-east-1:123:instance/i-new")

        # Simulate DB having an old resource that's no longer in cloud
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        from unittest.mock import MagicMock as MM
        old_resource = MM()
        old_resource.cloud_resource_id = "arn:aws:ec2:us-east-1:123:instance/i-old"
        old_resource.is_deleted = False

        mock_result = MM()
        mock_result.scalars.return_value.all.return_value = [old_resource]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session

        with patch("app.services.discovery.ClientFactory") as mock_cf, \
             patch("app.services.discovery.BatchNormalizer") as mock_norm_cls:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_cf.create_client = MagicMock(return_value=mock_client)

            mock_norm = MagicMock()
            mock_norm.normalize_batch = MagicMock(return_value=[resource])
            mock_norm_cls.return_value = mock_norm

            svc = CloudDiscoveryService(
                account=account,
                producer=producer,
                db_session_factory=mock_factory,
            )
            # Patch _mark_missing_as_deleted to verify it's called
            svc._mark_missing_as_deleted = AsyncMock(return_value=1)
            result = await svc.discover_full(correlation_id="corr-456")

        svc._mark_missing_as_deleted.assert_called_once()

    def test_compute_hash_deterministic(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        producer = AsyncMock()
        svc = CloudDiscoveryService(account=account, producer=producer)
        resource = _make_resource()
        h1 = svc._compute_hash(resource)
        h2 = svc._compute_hash(resource)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_sanitize_for_json_handles_datetime(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        svc = CloudDiscoveryService(account=account, producer=AsyncMock())
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = svc._sanitize_for_json({"created": dt, "name": "test"})
        assert result["created"] == "2024-01-15T10:30:00"
        assert result["name"] == "test"

    def test_sanitize_for_json_handles_nested(self):
        from app.services.discovery import CloudDiscoveryService
        account = _make_account()
        svc = CloudDiscoveryService(account=account, producer=AsyncMock())
        data = {"nested": {"dt": datetime(2024, 1, 1), "list": [1, datetime(2024, 2, 1)]}}
        result = svc._sanitize_for_json(data)
        assert result["nested"]["dt"] == "2024-01-01T00:00:00"
        assert result["nested"]["list"][1] == "2024-02-01T00:00:00"
