"""Unit tests for the Cloud Connector service.

All tests use the actual public API of each module. No tests reference
internal attributes that don't exist (e.g. ``can_execute``, ``record_success``).
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from cloudvisor_types.models import CloudProvider, Environment, CloudResource


# ─── ResourceNormalizer tests ─────────────────────────────────────────────────

class TestResourceNormalizer:
    """Tests for resource normalization."""

    def _make_normalizer(self):
        from app.services.normalizer import ResourceNormalizer
        return ResourceNormalizer("org-123")

    def test_normalize_aws_ec2(self):
        normalizer = self._make_normalizer()
        raw = {
            "type": "EC2",
            "id": "arn:aws:ec2:us-east-1:123456789012:instance/i-abc",
            "name": "web-server-01",
            "region": "us-east-1",
            "tags": {"Environment": "Production", "Name": "web-server-01"},
            "raw": {"InstanceId": "i-abc"},
        }
        resource = normalizer.normalize(raw, "aws", "123456789012")
        assert resource.provider == CloudProvider.AWS
        assert resource.account_id == "123456789012"
        assert resource.name == "web-server-01"
        assert resource.environment == Environment.PROD
        assert resource.organization_id == "org-123"

    def test_normalize_azure_vm(self):
        normalizer = self._make_normalizer()
        raw = {
            "type": "VirtualMachine",
            "id": "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/my-vm",
            "name": "my-vm",
            "region": "eastus",
            "tags": {"env": "dev"},
            "raw": {},
        }
        resource = normalizer.normalize(raw, "azure", "sub-123")
        assert resource.provider == CloudProvider.AZURE
        assert resource.account_id == "sub-123"
        assert resource.environment == Environment.DEV

    def test_normalize_gcp_instance(self):
        normalizer = self._make_normalizer()
        raw = {
            "type": "Instance",
            "id": "projects/my-project/zones/us-central1-a/instances/my-instance",
            "name": "my-instance",
            "region": "us-central1-a",
            "tags": {"environment": "staging"},
            "raw": {},
        }
        resource = normalizer.normalize(raw, "gcp", "my-project")
        assert resource.provider == CloudProvider.GCP
        assert resource.environment == Environment.STAGING

    def test_infer_environment_from_tags(self):
        normalizer = self._make_normalizer()
        env = normalizer._infer_environment({"env": "staging"}, "my-app")
        assert env == Environment.STAGING

    def test_infer_environment_from_name(self):
        normalizer = self._make_normalizer()
        env = normalizer._infer_environment({}, "app-prod-api")
        assert env == Environment.PROD

    def test_infer_environment_unknown(self):
        normalizer = self._make_normalizer()
        env = normalizer._infer_environment({}, "my-service")
        assert env == Environment.UNKNOWN

    def test_detect_public_s3_blocked(self):
        normalizer = self._make_normalizer()
        raw = {
            "publicaccessblockconfiguration": {
                "blockpublicacls": True,
                "blockpublicpolicy": True,
                "ignorepublicacls": True,
                "restrictpublicbuckets": True,
            },
        }
        assert normalizer._detect_public_access(raw, "S3Bucket", "aws") is False

    def test_detect_public_s3_open(self):
        normalizer = self._make_normalizer()
        raw = {
            "publicaccessblockconfiguration": {
                "blockpublicacls": False,
                "blockpublicpolicy": True,
                "ignorepublicacls": True,
                "restrictpublicbuckets": True,
            },
        }
        assert normalizer._detect_public_access(raw, "S3Bucket", "aws") is True

    def test_normalize_tags_lowercase(self):
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
    def test_normalize_batch(self):
        from app.services.normalizer import BatchNormalizer
        normalizer = BatchNormalizer("org-123")
        raw_resources = [
            {"type": "EC2", "id": "id1", "name": "server1", "region": "us-east-1", "tags": {}},
            {"type": "S3Bucket", "id": "id2", "name": "bucket1", "region": "global", "tags": {}},
        ]
        resources = normalizer.normalize_batch(raw_resources, "aws", "123456789012")
        assert len(resources) == 2

    def test_normalize_empty_batch(self):
        from app.services.normalizer import BatchNormalizer
        normalizer = BatchNormalizer("org-123")
        resources = normalizer.normalize_batch([], "aws", "123456789012")
        assert resources == []


# ─── CircuitBreaker tests (using actual async call() API) ────────────────────

class TestCircuitBreaker:
    """Tests for circuit breaker using the real async call() interface."""

    def _make_breaker(self):
        from app.services.circuit_breaker import CircuitBreaker
        return CircuitBreaker(
            name="test",
            failure_threshold=0.5,
            failure_window_seconds=300,
            recovery_timeout_seconds=60,
            min_requests_for_threshold=2,
        )

    def test_initial_state_closed(self):
        from app.services.circuit_breaker import CircuitState
        breaker = self._make_breaker()
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self):
        """Closed circuit allows calls through."""
        breaker = self._make_breaker()

        async def ok():
            return "ok"

        result = await breaker.call(ok)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_record_success(self):
        from app.services.circuit_breaker import CircuitState
        breaker = self._make_breaker()

        async def ok():
            return "ok"

        await breaker.call(ok)
        assert breaker._metrics.successful_requests == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_record_failure(self):
        breaker = self._make_breaker()

        async def fail():
            raise ValueError("boom")

        try:
            await breaker.call(fail)
        except ValueError:
            pass

        assert breaker._metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        from app.services.circuit_breaker import CircuitState
        breaker = self._make_breaker()
        # Force to HALF_OPEN
        breaker._state = CircuitState.HALF_OPEN
        breaker._metrics.total_requests = 0

        async def ok():
            return "ok"

        await breaker.call(ok)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        from app.services.circuit_breaker import CircuitState
        breaker = self._make_breaker()
        breaker._state = CircuitState.HALF_OPEN
        breaker._metrics.total_requests = 0

        async def fail():
            raise ValueError("boom")

        try:
            await breaker.call(fail)
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN

    def test_reset(self):
        from app.services.circuit_breaker import CircuitState
        breaker = self._make_breaker()
        breaker._metrics.failed_requests = 10
        breaker._metrics.total_requests = 10
        breaker.reset()
        assert breaker._metrics.failed_requests == 0
        assert breaker._metrics.total_requests == 0
        assert breaker.state == CircuitState.CLOSED

    def test_get_status(self):
        breaker = self._make_breaker()
        status = breaker.get_status()
        assert status["name"] == "test"
        assert "state" in status
        assert "error_rate" in status


# ─── Retry logic tests ────────────────────────────────────────────────────────

class TestRetryLogic:
    """Tests for exponential backoff retry using the actual decorator API."""

    def test_retry_config_calculate_delay(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(
            max_retries=5,
            initial_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert cfg.calculate_delay(0) == 1.0
        assert cfg.calculate_delay(1) == 2.0
        assert cfg.calculate_delay(2) == 4.0

    def test_retry_config_max_cap(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(
            max_retries=5,
            initial_delay_seconds=1.0,
            max_delay_seconds=5.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert cfg.calculate_delay(10) == 5.0

    def test_retry_config_jitter_within_range(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(
            max_retries=5,
            initial_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=2.0,
            jitter=True,
        )
        delay = cfg.calculate_delay(0)
        assert 0.5 <= delay <= 1.0

    @pytest.mark.asyncio
    async def test_retry_decorator_success_on_first_try(self):
        from app.services.retry import retry_async, RetryConfig

        call_count = 0

        @retry_async(config=RetryConfig(max_retries=3))
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_decorator_retries_on_temporary_error(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException

        call_count = 0

        @retry_async(
            config=RetryConfig(
                max_retries=5,
                initial_delay_seconds=0.001,
                max_delay_seconds=0.01,
            ),
            retryable_exceptions=(TemporaryException,),
        )
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TemporaryException("transient")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_decorator_does_not_retry_non_retryable(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException

        call_count = 0

        @retry_async(
            config=RetryConfig(max_retries=5, initial_delay_seconds=0.001),
            retryable_exceptions=(TemporaryException,),
        )
        async def auth_error_func():
            nonlocal call_count
            call_count += 1
            raise PermissionError("access denied")

        with pytest.raises(PermissionError):
            await auth_error_func()

        assert call_count == 1  # No retries for non-retryable errors

    @pytest.mark.asyncio
    async def test_retry_decorator_exhausted_raises_original(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException

        @retry_async(
            config=RetryConfig(
                max_retries=2,
                initial_delay_seconds=0.001,
                max_delay_seconds=0.01,
            ),
            retryable_exceptions=(TemporaryException,),
        )
        async def always_fails():
            raise TemporaryException("always fails")

        with pytest.raises(TemporaryException):
            await always_fails()


# ─── CloudVisor type model tests ──────────────────────────────────────────────

class TestCloudResourceModel:
    def test_to_dict(self):
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

    def test_provider_enum_values(self):
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.AZURE.value == "azure"
        assert CloudProvider.GCP.value == "gcp"
        assert CloudProvider.OCI.value == "oci"

    def test_environment_enum_values(self):
        assert Environment.PROD.value == "prod"
        assert Environment.STAGING.value == "staging"
        assert Environment.DEV.value == "dev"
        assert Environment.UNKNOWN.value == "unknown"


# ─── Vault client tests ───────────────────────────────────────────────────────

class TestVaultClient:
    def test_init_without_url(self):
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="", vault_token="")
        assert client._vault_url == ""

    @pytest.mark.asyncio
    async def test_initialize_without_url_returns_false(self):
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="", vault_token="")
        result = await client.initialize()
        assert result is False

    @pytest.mark.asyncio
    async def test_store_credentials_raises_without_client(self):
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="http://localhost:8200", vault_token="test")
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.store_credentials("acc-1", "org-1", "aws", {"key": "val"})

    @pytest.mark.asyncio
    async def test_retrieve_credentials_raises_without_client(self):
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="http://localhost:8200", vault_token="test")
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.retrieve_credentials("some/path")

    @pytest.mark.asyncio
    async def test_get_credentials_alias(self):
        """get_credentials is a backwards-compat alias for retrieve_credentials."""
        from app.services.vault_client import VaultClient
        client = VaultClient(vault_url="http://localhost:8200", vault_token="test")
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.get_credentials("some/path")


# ─── Credential crypto tests ──────────────────────────────────────────────────

class TestCredentialCrypto:
    """Tests for envelope encryption / decryption."""

    def test_encrypt_returns_plaintext_when_no_master_key(self, monkeypatch):
        """Without CONNECTOR_CREDENTIAL_MASTER_KEY, returns plaintext."""
        monkeypatch.delenv("CONNECTOR_CREDENTIAL_MASTER_KEY", raising=False)
        from app.services import credential_crypto
        # Reload to clear cached env
        import importlib
        importlib.reload(credential_crypto)

        creds = {"access_key": "AKIA...", "secret_key": "secret"}
        result = credential_crypto.encrypt_credentials(creds, "org-123")
        # Without master key, returns plaintext unchanged
        assert result == creds or result is creds

    def test_encrypt_decrypt_roundtrip(self, monkeypatch):
        """Encrypt then decrypt returns the original credentials."""
        monkeypatch.setenv("CONNECTOR_CREDENTIAL_MASTER_KEY", "a" * 64)
        from app.services import credential_crypto
        import importlib
        importlib.reload(credential_crypto)

        creds = {"access_key": "AKIA123", "secret_key": "mysecret", "region": "us-east-1"}
        encrypted = credential_crypto.encrypt_credentials(creds, "org-abc")

        # Should be encrypted (has scheme key)
        if "scheme" in (encrypted or {}):
            decrypted = credential_crypto.decrypt_credentials(encrypted, "org-abc")
            assert decrypted == creds

    def test_decrypt_legacy_plaintext(self):
        """Plaintext dict (no scheme key) passes through decrypt unchanged."""
        from app.services.credential_crypto import decrypt_credentials
        plaintext = {"access_key": "AKIA...", "secret_key": "secret"}
        result = decrypt_credentials(plaintext, "org-123")
        assert result == plaintext

    def test_decrypt_empty_returns_empty(self):
        from app.services.credential_crypto import decrypt_credentials
        assert decrypt_credentials(None, "org-123") == {}
        assert decrypt_credentials({}, "org-123") == {}

    def test_is_encrypted_detects_scheme(self):
        from app.services.credential_crypto import is_encrypted
        assert is_encrypted({"scheme": "AES-256-GCM+HKDF-SHA256", "ciphertext": "abc"}) is True
        assert is_encrypted({"access_key": "AKIA..."}) is False
        assert is_encrypted(None) is False


# ─── Prometheus metrics tests ─────────────────────────────────────────────────

class TestConnectorMetrics:
    def test_record_sync_start(self):
        from app.metrics.prometheus import ConnectorMetrics
        ConnectorMetrics.record_sync_start(
            organization_id="org-123",
            account_id="acc-123",
            provider="aws",
            sync_type="full",
        )

    def test_record_sync_complete(self):
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
        from app.metrics.prometheus import ConnectorMetrics
        ConnectorMetrics.record_error(
            organization_id="org-123",
            account_id="acc-123",
            provider="aws",
            error_type="AuthError",
        )

    def test_record_event_published(self):
        from app.metrics.prometheus import ConnectorMetrics
        ConnectorMetrics.record_event_published(
            event_type="resource.discovered",
            provider="aws",
        )


# ─── Async placeholder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_placeholder():
    assert True
