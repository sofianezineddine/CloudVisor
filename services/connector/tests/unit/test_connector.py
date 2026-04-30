"""Unit tests for the Cloud Connector service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from cloudvisor_types.models import CloudProvider, Environment, CloudResource, CloudAccount


# ─── ResourceNormalizer tests ─────────────────────────────────────────────────

class TestResourceNormalizer:
    """Tests for resource normalization."""

    def _make_normalizer(self):
        from app.services.normalizer import ResourceNormalizer
        return ResourceNormalizer("org-123")

    def test_normalize_aws_ec2(self):
        """Test normalizing an AWS EC2 instance."""
        normalizer = self._make_normalizer()

        raw_resource = {
            "type": "EC2",
            "id": "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
            "name": "web-server-01",
            "region": "us-east-1",
            "tags": {"Environment": "Production", "Name": "web-server-01"},
            "raw": {"InstanceId": "i-1234567890abcdef0"},
        }

        resource = normalizer.normalize(raw_resource, "aws", "123456789012")

        assert resource.provider == CloudProvider.AWS
        assert resource.account_id == "123456789012"
        assert resource.resource_type == "aws::ec2::instance"
        assert resource.name == "web-server-01"
        assert resource.environment == Environment.PROD
        assert resource.organization_id == "org-123"

    def test_normalize_azure_vm(self):
        """Test normalizing an Azure Virtual Machine."""
        normalizer = self._make_normalizer()

        raw_resource = {
            "type": "VirtualMachine",
            "id": "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/my-vm",
            "name": "my-vm",
            "region": "eastus",
            "tags": {"env": "dev"},
            "raw": {"id": "/subscriptions/sub-123/..."},
        }

        resource = normalizer.normalize(raw_resource, "azure", "sub-123")

        assert resource.provider == CloudProvider.AZURE
        assert resource.account_id == "sub-123"
        assert resource.resource_type == "azure::virtualmachine::instance"
        assert resource.environment == Environment.DEV

    def test_normalize_gcp_instance(self):
        """Test normalizing a GCP Compute Instance."""
        normalizer = self._make_normalizer()

        raw_resource = {
            "type": "Instance",
            "id": "projects/my-project/zones/us-central1-a/instances/my-instance",
            "name": "my-instance",
            "region": "us-central1-a",
            "tags": {"environment": "staging"},
            "raw": {"name": "my-instance"},
        }

        resource = normalizer.normalize(raw_resource, "gcp", "my-project")

        assert resource.provider == CloudProvider.GCP
        assert resource.environment == Environment.STAGING

    def test_infer_environment_from_tags(self):
        """Test environment inference from tags."""
        normalizer = self._make_normalizer()

        tags = {"env": "staging", "team": "platform"}
        env = normalizer._infer_environment(tags, "my-app")

        assert env == Environment.STAGING

    def test_infer_environment_from_name(self):
        """Test environment inference from resource name."""
        normalizer = self._make_normalizer()

        tags = {"team": "platform"}
        env = normalizer._infer_environment(tags, "app-prod-api")

        assert env == Environment.PROD

    def test_infer_environment_unknown(self):
        """Test environment defaults to UNKNOWN when no hints."""
        normalizer = self._make_normalizer()

        tags = {"team": "platform"}
        env = normalizer._infer_environment(tags, "my-service")

        assert env == Environment.UNKNOWN

    def test_detect_public_s3_blocked(self):
        """Test public access detection for S3 with block enabled."""
        normalizer = self._make_normalizer()

        raw = {
            "type": "S3Bucket",
            "id": "arn:aws:s3:::my-bucket",
            "name": "my-bucket",
            "publicaccessblockconfiguration": {
                "blockpublicacls": True,
                "blockpublicpolicy": True,
                "ignorepublicacls": True,
                "restrictpublicbuckets": True,
            },
        }

        is_public = normalizer._detect_public_access(raw, "S3Bucket", "aws")
        assert is_public is False

    def test_detect_public_s3_open(self):
        """Test public access detection for S3 with block disabled."""
        normalizer = self._make_normalizer()

        raw = {
            "type": "S3Bucket",
            "id": "arn:aws:s3:::my-bucket",
            "name": "my-bucket",
            "publicaccessblockconfiguration": {
                "blockpublicacls": False,
                "blockpublicpolicy": True,
                "ignorepublicacls": True,
                "restrictpublicbuckets": True,
            },
        }

        is_public = normalizer._detect_public_access(raw, "S3Bucket", "aws")
        assert is_public is True

    def test_normalize_tags_lowercase(self):
        """Test that tags are normalized to lowercase."""
        normalizer = self._make_normalizer()

        raw = {
            "type": "EC2",
            "id": "i-123",
            "name": "server",
            "region": "us-east-1",
            "tags": {"Environment": "PROD", "Team": "Platform"},
            "raw": {},
        }

        resource = normalizer.normalize(raw, "aws", "123456789012")
        assert resource.tags.get("environment") == "prod"
        assert resource.tags.get("team") == "platform"


# ─── BatchNormalizer tests ────────────────────────────────────────────────────

class TestBatchNormalizer:
    """Tests for batch normalization."""

    def test_normalize_batch(self):
        """Test batch normalization."""
        from app.services.normalizer import BatchNormalizer
        normalizer = BatchNormalizer("org-123")

        raw_resources = [
            {"type": "EC2", "id": "id1", "name": "server1", "region": "us-east-1", "tags": {}},
            {"type": "S3Bucket", "id": "id2", "name": "bucket1", "region": "global", "tags": {}},
        ]

        resources = normalizer.normalize_batch(raw_resources, "aws", "123456789012")

        assert len(resources) == 2
        assert resources[0].resource_type == "aws::ec2::instance"
        assert resources[1].resource_type == "aws::s3bucket::instance"

    def test_normalize_empty_batch(self):
        """Test normalizing an empty batch."""
        from app.services.normalizer import BatchNormalizer
        normalizer = BatchNormalizer("org-123")

        resources = normalizer.normalize_batch([], "aws", "123456789012")
        assert resources == []


# ─── CircuitBreaker tests ─────────────────────────────────────────────────────

class TestCircuitBreaker:
    """Tests for circuit breaker."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts in closed state."""
        from app.services.circuit_breaker import CircuitBreaker, CircuitState
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED

    def test_can_execute_when_closed(self):
        """Test execution is allowed when circuit is closed."""
        from app.services.circuit_breaker import CircuitBreaker
        breaker = CircuitBreaker(name="test")
        assert breaker.can_execute() is True

    def test_record_success(self):
        """Test recording a success."""
        from app.services.circuit_breaker import CircuitBreaker, CircuitState
        breaker = CircuitBreaker(name="test")
        breaker.record_success()
        assert breaker._successes == 1
        assert breaker.state == CircuitState.CLOSED

    def test_record_failure(self):
        """Test recording a failure."""
        from app.services.circuit_breaker import CircuitBreaker
        breaker = CircuitBreaker(name="test")
        breaker.record_failure()
        assert breaker._failures == 1

    def test_half_open_success_closes_circuit(self):
        """Test successful call in half-open state closes circuit."""
        from app.services.circuit_breaker import CircuitBreaker, CircuitState
        breaker = CircuitBreaker(name="test")
        breaker._state = CircuitState.HALF_OPEN
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        """Test failed call in half-open state reopens circuit."""
        from app.services.circuit_breaker import CircuitBreaker, CircuitState
        breaker = CircuitBreaker(name="test")
        breaker._state = CircuitState.HALF_OPEN
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_reset(self):
        """Test circuit breaker reset."""
        from app.services.circuit_breaker import CircuitBreaker, CircuitState
        breaker = CircuitBreaker(name="test")
        breaker._failures = 10
        breaker._successes = 5
        breaker.reset()
        assert breaker._failures == 0
        assert breaker._successes == 0
        assert breaker.state == CircuitState.CLOSED

    def test_get_status(self):
        """Test status reporting."""
        from app.services.circuit_breaker import CircuitBreaker
        breaker = CircuitBreaker(name="test-breaker")
        status = breaker.get_status()
        assert status["name"] == "test-breaker"
        assert "state" in status
        assert "error_rate" in status


# ─── Retry logic tests ────────────────────────────────────────────────────────

class TestRetryLogic:
    """Tests for exponential backoff retry."""

    def test_calculate_delay_base(self):
        """Test base delay calculation."""
        from app.services.retry import calculate_delay
        delay = calculate_delay(0, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=False)
        assert delay == 1.0

    def test_calculate_delay_exponential(self):
        """Test exponential delay growth."""
        from app.services.retry import calculate_delay
        delay0 = calculate_delay(0, 1.0, 60.0, 2.0, jitter=False)
        delay1 = calculate_delay(1, 1.0, 60.0, 2.0, jitter=False)
        delay2 = calculate_delay(2, 1.0, 60.0, 2.0, jitter=False)
        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_calculate_delay_max_cap(self):
        """Test delay is capped at max."""
        from app.services.retry import calculate_delay
        delay = calculate_delay(10, base_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)
        assert delay == 5.0

    def test_calculate_delay_with_jitter(self):
        """Test delay with jitter is within expected range."""
        from app.services.retry import calculate_delay
        delay = calculate_delay(0, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True)
        # With jitter: delay = base * (0.5 to 1.0)
        assert 0.5 <= delay <= 1.0

    @pytest.mark.asyncio
    async def test_retry_success_on_first_try(self):
        """Test successful function doesn't retry."""
        from app.services.retry import retry_async, RetryConfig

        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(success_func, retry_config=RetryConfig(max_retries=3))
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test function retries and eventually succeeds."""
        from app.services.retry import retry_async, RetryConfig

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await retry_async(
            flaky_func,
            retry_config=RetryConfig(max_retries=5, base_delay=0.01),
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        """Test RetryError raised when all retries exhausted."""
        from app.services.retry import retry_async, RetryConfig, RetryError

        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            await retry_async(
                always_fails,
                retry_config=RetryConfig(max_retries=2, base_delay=0.01),
            )


# ─── CloudVisor type model tests ──────────────────────────────────────────────

class TestCloudResourceModel:
    """Tests for CloudResource dataclass."""

    def test_to_dict(self):
        """Test CloudResource serialization."""
        resource = CloudResource(
            id="res-123",
            cloud_resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-123",
            provider=CloudProvider.AWS,
            account_id="123456789012",
            region="us-east-1",
            resource_type="aws::ec2::instance",
            name="test-instance",
            tags={"env": "prod"},
            raw={"InstanceId": "i-123"},
            organization_id="org-123",
            is_public=False,
            environment=Environment.PROD,
            first_seen_at=datetime(2024, 1, 1, 0, 0, 0),
            last_seen_at=datetime(2024, 1, 2, 0, 0, 0),
        )

        data = resource.to_dict()

        assert data["id"] == "res-123"
        assert data["provider"] == "aws"
        assert data["environment"] == "prod"
        assert data["is_public"] is False
        assert data["first_seen_at"] == "2024-01-01T00:00:00"

    def test_provider_enum_values(self):
        """Test CloudProvider enum values."""
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.AZURE.value == "azure"
        assert CloudProvider.GCP.value == "gcp"
        assert CloudProvider.OCI.value == "oci"

    def test_environment_enum_values(self):
        """Test Environment enum values."""
        assert Environment.PROD.value == "prod"
        assert Environment.STAGING.value == "staging"
        assert Environment.DEV.value == "dev"
        assert Environment.UNKNOWN.value == "unknown"


class TestCloudAccountModel:
    """Tests for CloudAccount dataclass."""

    def test_to_dict(self):
        """Test CloudAccount serialization."""
        account = CloudAccount(
            id="acc-123",
            organization_id="org-123",
            provider=CloudProvider.AWS,
            name="Production AWS",
            account_id="123456789012",
            status="active",
        )

        data = account.to_dict()

        assert data["id"] == "acc-123"
        assert data["provider"] == "aws"
        assert data["status"] == "active"
        assert data["organization_id"] == "org-123"

    def test_default_values(self):
        """Test CloudAccount default field values."""
        account = CloudAccount(
            id="acc-123",
            organization_id="org-123",
            provider=CloudProvider.GCP,
            name="My GCP Project",
            account_id="my-project",
        )

        assert account.status == "pending"
        assert account.region == "global"
        assert account.polling_interval_minutes == 15
        assert account.resource_count == 0
        assert account.consecutive_errors == 0


# ─── Vault client tests ───────────────────────────────────────────────────────

class TestVaultClient:
    """Tests for Vault credential storage."""

    def test_init_without_url(self):
        """Test VaultClient initializes without URL (disabled mode)."""
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="", vault_token="")
        assert client._vault_url == ""

    @pytest.mark.asyncio
    async def test_initialize_without_url_returns_false(self):
        """Test initialize returns False when URL not configured."""
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="", vault_token="")
        result = await client.initialize()
        assert result is False

    @pytest.mark.asyncio
    async def test_store_credentials_raises_without_client(self):
        """Test store_credentials raises when not initialized."""
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="http://localhost:8200", vault_token="test")
        # _client is None — not initialized
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.store_credentials("acc-1", "org-1", "aws", {"key": "val"})


# ─── Prometheus metrics tests ─────────────────────────────────────────────────

class TestConnectorMetrics:
    """Tests for Prometheus metrics recording."""

    def test_record_sync_start(self):
        """Test sync start metric recording doesn't raise."""
        from app.metrics.prometheus import ConnectorMetrics
        # Should not raise
        ConnectorMetrics.record_sync_start(
            organization_id="org-123",
            account_id="acc-123",
            provider="aws",
            sync_type="full",
        )

    def test_record_sync_complete(self):
        """Test sync complete metric recording."""
        from app.metrics.prometheus import ConnectorMetrics
        ConnectorMetrics.record_sync_complete(
            organization_id="org-123",
            account_id="acc-123",
            provider="aws",
            sync_type="full",
            status="completed",
            duration_seconds=42.5,
            discovered=100,
            updated=10,
            deleted=5,
            errors=0,
            resource_count=100,
        )

    def test_record_error(self):
        """Test error metric recording."""
        from app.metrics.prometheus import ConnectorMetrics
        ConnectorMetrics.record_error(
            organization_id="org-123",
            account_id="acc-123",
            provider="aws",
            error_type="AuthError",
        )

    def test_record_event_published(self):
        """Test event published metric recording."""
        from app.metrics.prometheus import ConnectorMetrics
        ConnectorMetrics.record_event_published(
            event_type="resource.discovered",
            provider="aws",
        )


# ─── Async placeholder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_placeholder():
    """Placeholder async test."""
    assert True
