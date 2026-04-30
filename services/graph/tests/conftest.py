"""Pytest configuration for graph service."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "types" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "utils" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
