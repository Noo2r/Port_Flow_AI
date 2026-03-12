"""Tests for GET /api/v1/health"""
import pytest


# --- Unit tests (no DB) ---

def test_health_returns_200(unit_client):
    r = unit_client.get("/api/v1/health")
    assert r.status_code == 200


def test_health_schema(unit_client):
    r = unit_client.get("/api/v1/health")
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert "timestamp" in data
    assert data["app"] == "PortFlow AI"


def test_root_returns_200(unit_client):
    r = unit_client.get("/")
    assert r.status_code == 200
    assert r.json()["message"] == "Welcome to PortFlow AI"


# --- Integration tests (requires docker compose up) ---

@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_live(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_docs_available(client):
    r = await client.get("/docs")
    assert r.status_code == 200
