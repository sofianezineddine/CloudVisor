"""Pytest configuration for graph service."""

import os
import sys
from pathlib import Path

# Add the graph service root to sys.path so `app.*` imports work
_service_root = Path(__file__).parent.parent
sys.path.insert(0, str(_service_root))

# Add shared packages to sys.path
_repo_root = _service_root.parent.parent
sys.path.insert(0, str(_repo_root / "packages" / "types" / "src"))
sys.path.insert(0, str(_repo_root / "packages" / "utils" / "src"))

# Set minimal env vars so settings don't fail during unit tests
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
