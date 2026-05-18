"""
Shared test fixtures for the API gateway service tests.
"""

import pytest
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.auth import AuthenticatedUser


@pytest.fixture
def mock_user():
    """Create a mock authenticated user for testing."""
    payload = {
        "sub": "user_123",
        "org_id": "org_456",
        "role": "admin",
        "session_id": "sess_789",
    }
    return AuthenticatedUser(payload, "fake_jwt_token")
