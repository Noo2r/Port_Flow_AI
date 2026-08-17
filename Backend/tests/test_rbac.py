"""
TC-BE-RBAC — Role-Based Access Control tests
============================================================
Verifies that the TECHNICAL-bucket restrictions (Task 1) are enforced:

  - GET  /api/v1/eta/evaluation
  - POST /api/v1/eta/set-active-model
  - GET  /api/v1/congestion/evaluation
  - GET  /api/v1/analytics/metrics
  - GET  /api/v1/analytics/charts
  - GET  /api/v1/analytics/metrics/compare

All tests are *unit* tests (no real DB, no real Redis).
The auth dependency is overridden to inject a mock user with the desired role.
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.iam import UserRole


# ── Helpers ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _noop_lifespan(app):
    yield


def _mock_db():
    mock = MagicMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value = MagicMock(all=lambda: [], first=lambda: None)
    result_mock.scalar.return_value = 0
    result_mock.scalar_one.return_value = 0
    result_mock.scalar_one_or_none.return_value = None
    result_mock.first.return_value = None
    result_mock.mappings.return_value = MagicMock(first=lambda: None, all=lambda: [])
    mock.execute = AsyncMock(return_value=result_mock)
    mock.get = AsyncMock(return_value=None)
    mock.add = MagicMock()
    mock.add_all = MagicMock()
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock


@pytest.fixture
def role_client(request):
    """
    Pytest fixture that yields a TestClient with `get_current_user` overriding
    to inject a user with the role passed via `request.param`.

    Usage (parametrize marker required):
        @pytest.mark.parametrize("role_client", [UserRole.ADMIN], indirect=True)
        def test_foo(role_client): ...
    """
    from app.main import app

    role = request.param
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = role
    mock_user.is_active = True

    mock_db = _mock_db()

    async def override_db():
        yield mock_db

    async def override_user():
        return mock_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    with patch.object(app.router, "lifespan_context", _noop_lifespan):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()


# ── Parametrized TECHNICAL-bucket endpoints ───────────────────────────────────

TECHNICAL_ENDPOINTS = [
    ("GET",  "/api/v1/analytics/metrics"),
    ("GET",  "/api/v1/analytics/charts"),
    ("GET",  "/api/v1/analytics/metrics/compare"),
    ("GET",  "/api/v1/congestion/evaluation"),
    # eta router is mounted at /ai (not /eta) — see app/api/v1/router.py
    ("GET",  "/api/v1/ai/evaluation"),
]

TECHNICAL_ROLES   = [UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.ANALYST]
OPERATIONAL_ROLES = [UserRole.OPERATIONS, UserRole.VESSEL_AGENT, UserRole.READONLY]


@pytest.mark.parametrize("role_client", TECHNICAL_ROLES, indirect=True)
@pytest.mark.parametrize("method,path", TECHNICAL_ENDPOINTS)
def test_technical_endpoint_allowed_for_technical_role(method, path, role_client):
    """ADMIN / PORT_MANAGER / ANALYST must not receive 403 on technical endpoints."""
    r = role_client.request(method, path)
    assert r.status_code != 403, (
        f"Technical role should be allowed on {method} {path}, got 403"
    )


@pytest.mark.parametrize("role_client", OPERATIONAL_ROLES, indirect=True)
@pytest.mark.parametrize("method,path", TECHNICAL_ENDPOINTS)
def test_technical_endpoint_forbidden_for_operational_role(method, path, role_client):
    """OPERATIONS / VESSEL_AGENT / READONLY must receive 403 on technical endpoints."""
    r = role_client.request(method, path)
    assert r.status_code == 403, (
        f"Operational role should be forbidden on {method} {path}, got {r.status_code}"
    )


# ── set-active-model: stricter — only ADMIN / PORT_MANAGER ────────────────────

SET_MODEL_ALLOWED   = [UserRole.ADMIN, UserRole.PORT_MANAGER]
SET_MODEL_FORBIDDEN = [
    UserRole.OPERATIONS, UserRole.VESSEL_AGENT, UserRole.READONLY, UserRole.ANALYST
]


@pytest.mark.parametrize("role_client", SET_MODEL_ALLOWED, indirect=True)
def test_set_active_model_allowed_for_manager(role_client):
    """ADMIN and PORT_MANAGER may call POST /ai/set-active-model."""
    r = role_client.post("/api/v1/ai/set-active-model", json={"model_name": "catboost"})
    assert r.status_code != 403, (
        f"Should be allowed on POST /eta/set-active-model, got 403"
    )


@pytest.mark.parametrize("role_client", SET_MODEL_FORBIDDEN, indirect=True)
def test_set_active_model_forbidden_for_others(role_client):
    """All roles except ADMIN/PORT_MANAGER must receive 403 on POST /ai/set-active-model."""
    r = role_client.post("/api/v1/ai/set-active-model", json={"model_name": "catboost"})
    assert r.status_code == 403, (
        f"Should be forbidden on POST /eta/set-active-model, got {r.status_code}"
    )


# ── Unauthenticated (no token) → 401 ─────────────────────────────────────────

def test_technical_endpoint_requires_auth(unit_client):
    """A request without any token must receive 401 on analytics/metrics."""
    r = unit_client.get("/api/v1/analytics/metrics")
    assert r.status_code == 401

def test_ai_evaluation_requires_auth(unit_client):
    """A request without any token must receive 401 on /ai/evaluation."""
    r = unit_client.get("/api/v1/ai/evaluation")
    assert r.status_code == 401
