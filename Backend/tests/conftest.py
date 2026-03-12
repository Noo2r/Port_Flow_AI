"""
Shared fixtures for all tests.

Integration tests hit the running Docker containers (localhost:8000).
Unit tests use FastAPI's TestClient with a mocked database session.
"""
import uuid
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db

BASE_URL = "http://localhost:8000"


def uid() -> str:
    """Short unique suffix for test data (IMO numbers, berth codes, etc.)."""
    return uuid.uuid4().hex[:6].upper()

# ---------------------------------------------------------------------------
# Integration test fixture — requires `docker compose up` to be running
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    """Async HTTP client pointed at the live Docker stack."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Unit test fixtures — no real DB required
# ---------------------------------------------------------------------------

def _make_mock_session(return_value=None):
    """Return a mock AsyncSession that yields an empty result by default."""
    mock = MagicMock()
    mock.execute = AsyncMock(
        return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: return_value or []))
    )
    mock.get = AsyncMock(return_value=return_value)
    mock.add = MagicMock()
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock


@pytest.fixture
def mock_db():
    return _make_mock_session()


@pytest.fixture
def unit_client(mock_db):
    """TestClient with database dependency overridden by a mock session."""
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
