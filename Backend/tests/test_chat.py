"""
Tests for /api/v1/chat endpoints (AI Assistant / Chatbot).

ANTHROPIC_API_KEY is unset in the test environment (see conftest.py), so
every /message call deterministically routes through the rule-based
_fallback() path rather than calling the real Claude API — this lets us
test real keyword-routing and response-shaping logic without mocking an
LLM, while still exercising genuine application code (not just schema
validation).
"""
import pytest


# ── /suggestions ──────────────────────────────────────────────────────────────

def test_suggestions_requires_auth(unit_client):
    r = unit_client.get("/api/v1/chat/suggestions")
    assert r.status_code == 401


def test_suggestions_returns_questions(auth_unit_client):
    r = auth_unit_client.get("/api/v1/chat/suggestions")
    assert r.status_code == 200
    data = r.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


# ── /message — auth & validation ──────────────────────────────────────────────

def test_message_requires_auth(unit_client):
    r = unit_client.post("/api/v1/chat/message", json={"message": "hello"})
    assert r.status_code == 401


def test_message_missing_field_rejected(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={})
    assert r.status_code == 422


# ── /message — rule-based fallback routing (no ANTHROPIC_API_KEY) ────────────

def test_message_uses_rule_based_fallback_without_api_key(auth_unit_client):
    """Confirms the fallback path is actually exercised in this test env —
    if this ever returns model_used != 'rule-based', a real API key leaked
    into the test environment and the other fallback-routing tests below
    would be testing the wrong code path."""
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "hello there"})
    assert r.status_code == 200
    assert r.json()["model_used"] == "rule-based"


def test_kpi_question_calls_get_port_kpis_tool(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "what are the current KPIs?"})
    assert r.status_code == 200
    data = r.json()
    assert "get_port_kpis" in data["tool_calls_made"]
    assert "Port KPIs" in data["response"]


def test_berth_question_calls_get_berth_status_tool(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "show me berth utilization"})
    assert r.status_code == 200
    data = r.json()
    assert "get_berth_status" in data["tool_calls_made"]
    assert "Berth Status" in data["response"]


def test_congestion_question_calls_congestion_forecast_tool(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "show congestion forecast for 72 hours"})
    assert r.status_code == 200
    data = r.json()
    assert "get_congestion_forecast" in data["tool_calls_made"]
    assert "72h horizon" in data["response"]


def test_arrival_question_uses_48h_window_for_tomorrow(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "what's arriving tomorrow?"})
    assert r.status_code == 200
    data = r.json()
    assert "list_upcoming_arrivals" in data["tool_calls_made"]
    # mocked DB returns no vessels, so the 0-count branch's hour window must show
    assert "48 hours" in data["response"]


def test_unrecognized_message_returns_help_text(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "asdkjasdkj nonsense"})
    assert r.status_code == 200
    data = r.json()
    assert data["tool_calls_made"] == []
    assert "I can answer questions about live port operations" in data["response"]


def test_suggested_questions_match_message_category(auth_unit_client):
    r = auth_unit_client.post("/api/v1/chat/message", json={"message": "tell me about berths"})
    data = r.json()
    assert any("berth" in q.lower() for q in data["suggested_questions"])
