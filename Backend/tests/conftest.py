"""
Shared fixtures for all tests.

Integration tests hit the ISOLATED test stack (docker-compose.test.yml),
never the demo stack — see README.md "Testing" section. The test API runs
on port 8001 (demo API is 8000) against a separate Postgres database on
port 5433 (demo DB is 5432). This isolation is what makes it safe to run
the full integration suite without ever touching demo/production data.
Unit tests use FastAPI's TestClient with a mocked database session and
never make a real database connection at all.
"""
import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# ── Point the app at the ISOLATED test database (port 5433, db "portflow_test") ──
# before importing app — never the demo database (port 5432, db "portflow").
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://portflow_test:portflow_test@localhost:5433/portflow_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")
os.environ.setdefault("APP_NAME", "PortFlow AI")
os.environ.setdefault("APP_VERSION", "2.0.0")

from app.main import app  # noqa: E402  (must come after env setup)
from app.database import get_db  # noqa: E402

# Integration tests hit the isolated test API. The default (port 8001) is
# the *host-side* port mapping for docker-compose.test.yml's test_api
# service — correct when running `pytest` from the host machine.
#
# If you instead run pytest *inside* the test_api container itself (e.g.
# `docker compose -f docker-compose.test.yml exec test_api pytest tests/`),
# port 8001 doesn't exist in that container's own network namespace — only
# the demo API's container would coincidentally also expose something on
# 8000 from a *different* namespace, so this is unambiguous in practice, but
# you must explicitly set TEST_API_BASE_URL=http://localhost:8000 (the test
# container's own internal port) for that exec context. Never set it to the
# demo API's externally-reachable host:port — see README.md "Testing".
BASE_URL = os.environ.get("TEST_API_BASE_URL", "http://localhost:8001")


def uid() -> str:
    """Short unique suffix for test data (IMO numbers, berth codes, etc.)."""
    return uuid.uuid4().hex[:6].upper()


def pytest_collection_modifyitems(config, items):
    """
    Skip integration-marked tests with a clear message if the isolated test
    stack isn't reachable, instead of letting every one of them fail with a
    raw connection-refused error. Keeps `pytest` repeatable and runnable from
    a cold checkout — unit tests (the majority) always run regardless.
    """
    has_integration_tests = any(item.get_closest_marker("integration") for item in items)
    if not has_integration_tests:
        return

    import httpx
    try:
        httpx.get(f"{BASE_URL}/", timeout=2.0)
        reachable = True
    except httpx.ConnectError:
        reachable = False

    if reachable:
        return

    skip_marker = pytest.mark.skip(
        reason=(
            f"Isolated test stack unreachable at {BASE_URL}. Run "
            "`docker compose -f docker-compose.test.yml up -d --build` first. "
            "See README.md \"Testing\" section."
        )
    )
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_marker)


# ---------------------------------------------------------------------------
# Integration test fixture — requires the isolated test stack to be running
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    """Async HTTP client pointed at the live Docker stack."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as c:
        yield c


@pytest_asyncio.fixture
async def auth_client():
    """
    Async HTTP client pre-authenticated as a PORT_MANAGER user.

    The public registration endpoint always creates READONLY accounts (by
    design — roles can only be assigned by an ADMIN). We therefore log in as
    `manager@portflow.ai` which is seeded by `seed_defaults()` with role
    PORT_MANAGER and is always present in the isolated test stack.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "manager@portflow.ai", "password": "Admin1234!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = r.json().get("access_token", "")
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


# ---------------------------------------------------------------------------
# Unit test fixtures — no real DB, no real Redis, background tasks disabled
# ---------------------------------------------------------------------------

def _make_mock_session(return_value=None):
    """Return a mock AsyncSession that yields an empty result by default.

    Supports both result patterns used in the codebase:
      - result.scalars().all()         → list endpoints
      - result.scalar()                → aggregate/count queries (analytics)
      - result.scalar_one_or_none()    → single-row lookups
    """
    mock = MagicMock()

    # Build a rich result mock that covers all access patterns
    result_mock = MagicMock()
    result_mock.scalars.return_value = MagicMock(
        all=lambda: return_value if isinstance(return_value, list) else [],
        first=lambda: (return_value[0] if return_value else None),
    )
    result_mock.scalar.return_value = 0          # counts always return 0
    result_mock.scalar_one.return_value = 0      # used by analytics service
    result_mock.scalar_one_or_none.return_value = None
    result_mock.first.return_value = None

    mock.execute = AsyncMock(return_value=result_mock)
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


@asynccontextmanager
async def _noop_lifespan(app):
    """Stub lifespan that skips DB seed, Redis connect, and background tasks."""
    yield



@pytest.fixture
def auth_unit_client(mock_db):
    """
    Unit TestClient with mocked DB AND mocked auth (admin user injected).
    Use for endpoints that require role-based auth but only need schema validation tested.
    """
    from app.core.dependencies import get_current_user
    from app.models.iam import UserRole

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = UserRole.ADMIN
    mock_user.is_active = True

    async def override_get_db():
        yield mock_db

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with patch.object(app.router, "lifespan_context", _noop_lifespan):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()

@pytest.fixture
def unit_client(mock_db):
    """
    TestClient with:
      - database session dependency replaced by a mock
      - lifespan replaced by a no-op (skips DB seed + background tasks)
    """
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    # Patch lifespan so TestClient doesn't try to reach Docker's DB/Redis
    with patch.object(app.router, "lifespan_context", _noop_lifespan):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
