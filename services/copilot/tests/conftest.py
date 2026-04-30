"""Pytest configuration and fixtures for Copilot service tests."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base


@pytest.fixture
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        "postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor_test",
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create a test database session."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def mock_claude_client(mocker):
    """Mock Claude API client."""
    mock = mocker.patch("app.services.llm_client.ClaudeClient")
    mock.return_value.generate.return_value = "Mocked Claude response"
    return mock


@pytest.fixture
def mock_retriever(mocker):
    """Mock context retriever."""
    mock = mocker.patch("app.services.retriever.ContextRetriever")
    mock.return_value.retrieve.return_value = {
        "intent": "POSTURE",
        "sources_used": ["asset_graph", "findings"],
        "assets": [],
        "findings": [],
    }
    return mock
