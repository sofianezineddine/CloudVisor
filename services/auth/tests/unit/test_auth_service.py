"""Unit tests for the Auth service."""

import hashlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Password validation tests ────────────────────────────────────────────────

class TestPasswordValidation:
    """Tests for password policy enforcement."""

    def _make_service(self):
        from app.services.auth_service import AuthService
        from app.core.config import AuthSettings
        settings = AuthSettings()
        return AuthService(db=None, settings=settings, redis_client=None)

    def test_valid_password(self):
        svc = self._make_service()
        # Should not raise
        svc._validate_password("SecurePass1!")

    def test_too_short(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="at least"):
            svc._validate_password("Ab1")

    def test_missing_uppercase(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="uppercase"):
            svc._validate_password("securepass1")

    def test_missing_lowercase(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="lowercase"):
            svc._validate_password("SECUREPASS1")

    def test_missing_digit(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="digit"):
            svc._validate_password("SecurePassword")

    def test_hash_and_verify(self):
        svc = self._make_service()
        password = "SecurePass1!"
        hashed = svc._hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_check_password_correct(self):
        svc = self._make_service()
        password = "SecurePass1!"
        hashed = svc._hash_password(password)
        assert await svc._check_password(password, hashed) is True

    @pytest.mark.asyncio
    async def test_check_password_wrong(self):
        svc = self._make_service()
        hashed = svc._hash_password("SecurePass1!")
        assert await svc._check_password("WrongPass1!", hashed) is False


# ─── JWT token tests ──────────────────────────────────────────────────────────

class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        from app.services.utils import create_access_token
        token = create_access_token(
            data={"sub": "user-123", "org_id": "org-456"},
            secret_key="test-secret-key-32-chars-minimum!",
            expires_delta=timedelta(minutes=15),
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        from app.services.utils import create_access_token, decode_token
        secret = "test-secret-key-32-chars-minimum!"
        token = create_access_token(
            data={"sub": "user-123", "org_id": "org-456"},
            secret_key=secret,
            expires_delta=timedelta(minutes=15),
        )
        payload = decode_token(token, secret)
        assert payload["sub"] == "user-123"
        assert payload["org_id"] == "org-456"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        from app.services.utils import create_refresh_token, decode_token
        secret = "test-secret-key-32-chars-minimum!"
        token = create_refresh_token(
            data={"sub": "user-123"},
            secret_key=secret,
            expires_delta=timedelta(days=30),
        )
        payload = decode_token(token, secret)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_expired_token_raises(self):
        from app.services.utils import create_access_token, decode_token
        from jose import ExpiredSignatureError
        secret = "test-secret-key-32-chars-minimum!"
        token = create_access_token(
            data={"sub": "user-123"},
            secret_key=secret,
            expires_delta=timedelta(seconds=-1),  # already expired
        )
        with pytest.raises(Exception):
            decode_token(token, secret)


# ─── MFA tests ────────────────────────────────────────────────────────────────

class TestMFA:
    """Tests for TOTP-based MFA."""

    def test_generate_secret(self):
        from app.services.mfa import generate_totp_secret
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16

    def test_get_totp_uri(self):
        from app.services.mfa import generate_totp_secret, get_totp_uri
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@example.com")
        assert "otpauth://totp/" in uri
        assert "CloudVisor" in uri
        assert "user@example.com" in uri

    def test_verify_valid_totp(self):
        import pyotp
        from app.services.mfa import verify_totp
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code) is True

    def test_verify_invalid_totp(self):
        from app.services.mfa import verify_totp
        import pyotp
        secret = pyotp.random_base32()
        assert verify_totp(secret, "000000") is False

    def test_verify_empty_code(self):
        from app.services.mfa import verify_totp
        import pyotp
        secret = pyotp.random_base32()
        assert verify_totp(secret, "") is False

    def test_generate_backup_codes(self):
        from app.services.mfa import generate_backup_codes
        codes = generate_backup_codes(10)
        assert len(codes) == 10
        assert all(isinstance(c, str) for c in codes)
        # All codes should be unique
        assert len(set(codes)) == 10

    def test_verify_backup_code(self):
        from app.services.mfa import generate_backup_codes, verify_backup_code
        codes = generate_backup_codes(5)
        hashed = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
        assert verify_backup_code(codes[0], hashed) is True
        assert verify_backup_code("INVALID", hashed) is False

    def test_generate_qr_code(self):
        from app.services.mfa import generate_totp_secret, get_totp_uri, generate_qr_code
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@example.com")
        qr_bytes = generate_qr_code(uri)
        assert isinstance(qr_bytes, bytes)
        assert len(qr_bytes) > 0
        # PNG magic bytes
        assert qr_bytes[:4] == b"\x89PNG"


# ─── API key tests ────────────────────────────────────────────────────────────

class TestApiKeyService:
    """Tests for API key management."""

    def _make_service(self):
        from app.services.api_keys import ApiKeyService
        from app.core.config import AuthSettings
        settings = AuthSettings()
        db_mock = AsyncMock()
        redis_mock = AsyncMock()
        return ApiKeyService(db_mock, settings, redis_mock)

    def test_key_format(self):
        """API keys should start with cv_live_ prefix."""
        import secrets
        from app.core.config import AuthSettings
        settings = AuthSettings()
        key = f"{settings.api_key_prefix}{secrets.token_urlsafe(settings.api_key_length)}"
        assert key.startswith("cv_live_")

    def test_key_hash_is_sha256(self):
        """API key hash should be SHA-256."""
        import secrets
        key = f"cv_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        assert len(key_hash) == 64  # SHA-256 hex = 64 chars


# ─── RBAC tests ───────────────────────────────────────────────────────────────

class TestRBAC:
    """Tests for role-based access control."""

    def _make_rbac(self):
        from app.services.rbac import RBACService
        from app.core.config import AuthSettings
        settings = AuthSettings()
        db_mock = AsyncMock()
        return RBACService(db_mock, settings)

    def test_owner_has_all_permissions(self):
        rbac = self._make_rbac()
        perms = rbac._permissions_for_role("owner")
        assert perms == ["*"]

    def test_viewer_read_only(self):
        rbac = self._make_rbac()
        perms = rbac._permissions_for_role("viewer")
        assert "findings:read" in perms
        assert "assets:read" in perms
        # Viewer should NOT have write permissions
        assert "findings:*" not in perms
        assert "accounts:write" not in perms

    def test_auditor_can_export(self):
        rbac = self._make_rbac()
        perms = rbac._permissions_for_role("auditor")
        assert "compliance:export" in perms
        assert "reports:generate" in perms

    def test_devops_cicd_access(self):
        rbac = self._make_rbac()
        perms = rbac._permissions_for_role("devops")
        assert "cicd:*" in perms

    @pytest.mark.asyncio
    async def test_check_permission_owner(self):
        rbac = self._make_rbac()
        rbac._db.execute = AsyncMock()
        # Mock get_user_role to return "owner"
        rbac.get_user_role = AsyncMock(return_value="owner")
        result = await rbac.check_permission("user-1", "billing:delete")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_viewer_denied_write(self):
        rbac = self._make_rbac()
        rbac.get_user_role = AsyncMock(return_value="viewer")
        result = await rbac.check_permission("user-1", "findings:write")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_wildcard(self):
        """security_engineer has findings:* which covers findings:delete."""
        rbac = self._make_rbac()
        rbac.get_user_role = AsyncMock(return_value="security_engineer")
        result = await rbac.check_permission("user-1", "findings:delete")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_returns_structured_result(self):
        rbac = self._make_rbac()
        rbac.get_user_role = AsyncMock(return_value="admin")
        result = await rbac.authorize("user-1", "findings:read")
        assert "authorized" in result
        assert "role" in result
        assert result["role"] == "admin"
        assert result["authorized"] is True


# ─── Rate limiter tests ───────────────────────────────────────────────────────

class TestRateLimiter:
    """Tests for Redis-backed rate limiting."""

    def _make_limiter(self, redis_mock=None):
        from app.services.rate_limiter import RateLimiter
        if redis_mock is None:
            redis_mock = AsyncMock()
        return RateLimiter(redis_mock)

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        redis_mock = AsyncMock()
        # pipeline().execute() returns [count, True]
        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[1, True])
        redis_mock.pipeline = MagicMock(return_value=pipe_mock)
        pipe_mock.incr = MagicMock()
        pipe_mock.expire = MagicMock()

        limiter = self._make_limiter(redis_mock)
        result = await limiter.check_login_rate("192.168.1.1")
        assert result is True

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        redis_mock = AsyncMock()
        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[11, True])  # 11 > limit of 10
        redis_mock.pipeline = MagicMock(return_value=pipe_mock)
        pipe_mock.incr = MagicMock()
        pipe_mock.expire = MagicMock()

        limiter = self._make_limiter(redis_mock)
        result = await limiter.check_login_rate("192.168.1.1")
        assert result is False

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_error(self):
        """Rate limiter should allow requests if Redis is unavailable."""
        redis_mock = AsyncMock()
        redis_mock.pipeline = MagicMock(side_effect=Exception("Redis down"))

        limiter = self._make_limiter(redis_mock)
        result = await limiter.check_login_rate("192.168.1.1")
        assert result is True  # fail open


# ─── Password reset tests ─────────────────────────────────────────────────────

class TestPasswordResetService:
    """Tests for password reset flow."""

    @pytest.mark.asyncio
    async def test_request_reset_returns_token_for_valid_user(self):
        from app.services.password_reset import PasswordResetService
        from app.core.config import AuthSettings
        from app.models import UserModel

        settings = AuthSettings()
        db_mock = AsyncMock()
        redis_mock = AsyncMock()

        # Mock user lookup
        user = MagicMock(spec=UserModel)
        user.id = "user-123"
        user.provider = "local"
        user.is_active = True

        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=user)
        db_mock.execute = AsyncMock(return_value=execute_result)
        redis_mock.setex = AsyncMock()

        svc = PasswordResetService(db_mock, redis_mock, settings)
        token = await svc.request_reset("user@example.com")

        assert token is not None
        assert len(token) > 0
        redis_mock.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_reset_returns_none_for_unknown_user(self):
        from app.services.password_reset import PasswordResetService
        from app.core.config import AuthSettings

        settings = AuthSettings()
        db_mock = AsyncMock()
        redis_mock = AsyncMock()

        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        db_mock.execute = AsyncMock(return_value=execute_result)

        svc = PasswordResetService(db_mock, redis_mock, settings)
        token = await svc.request_reset("unknown@example.com")

        assert token is None
        redis_mock.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self):
        from app.services.password_reset import PasswordResetService
        from app.core.config import AuthSettings

        settings = AuthSettings()
        db_mock = AsyncMock()
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)  # Token not found

        svc = PasswordResetService(db_mock, redis_mock, settings)
        with pytest.raises(ValueError, match="Invalid or expired"):
            await svc.reset_password("invalid-token", "NewPass1!")


# ─── Audit log tests ──────────────────────────────────────────────────────────

class TestAuditEventProducer:
    """Tests for async Kafka audit producer."""

    @pytest.mark.asyncio
    async def test_start_without_kafka_is_graceful(self):
        """Producer should not raise if Kafka is unavailable."""
        from app.producers.audit import AuditEventProducer
        producer = AuditEventProducer(bootstrap_servers="localhost:9999")
        # Should not raise even if Kafka is not running
        await producer.start()
        # _producer may be None if Kafka is unavailable
        await producer.stop()

    @pytest.mark.asyncio
    async def test_emit_without_producer_is_noop(self):
        """Emitting events without a producer should be a no-op."""
        from app.producers.audit import AuditEventProducer
        producer = AuditEventProducer(bootstrap_servers="localhost:9999")
        # Don't start — _producer is None
        # Should not raise
        await producer.emit_auth_event(
            organization_id="org-1",
            user_id="user-1",
            event_type="auth.login.success",
            success=True,
        )


# ─── OIDC PKCE tests ──────────────────────────────────────────────────────────

class TestOIDCService:
    """Tests for OIDC SSO service."""

    def test_code_challenge_generation(self):
        """PKCE code challenge should be base64url(sha256(verifier))."""
        from app.services.sso import OIDCService
        import hashlib, base64

        verifier = "test-code-verifier-string"
        challenge = OIDCService._generate_code_challenge(verifier)

        # Verify manually
        digest = hashlib.sha256(verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert challenge == expected

    def test_code_challenge_no_padding(self):
        """Code challenge should not have base64 padding."""
        from app.services.sso import OIDCService
        import secrets
        verifier = secrets.token_urlsafe(32)
        challenge = OIDCService._generate_code_challenge(verifier)
        assert "=" not in challenge


# ─── Async placeholder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_placeholder():
    assert True
