"""Tests for the FastAPI routes.

`main` constructs an Anthropic client at import time (which reads
ANTHROPIC_API_KEY from the environment), so we set a dummy key before importing.
No network calls are made by these tests — `/health` is fully local, and we
don't exercise the LLM-backed parse endpoint here.
"""

from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "safecycle-backend"


def test_health_reports_version():
    response = client.get("/health")
    assert response.json()["version"] == app.version


def test_parse_input_requires_user_input():
    # Missing required field -> 422 from FastAPI validation, no LLM call.
    response = client.post("/api/parse-input", json={})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# /api/guidance
# --------------------------------------------------------------------------- #
def _parsed(**overrides) -> dict:
    """A valid ParsedScenario body with sensible defaults, overridable."""
    body = {
        "product": "yasmin",
        "cycleWeek": 1,
        "pillsMissed": 0,
        "hoursLate": None,
        "confidence": 1.0,
        "clarifyingQuestion": None,
    }
    body.update(overrides)
    return body


@pytest.fixture(autouse=True)
def _stub_phraser(monkeypatch):
    """Avoid real LLM calls: the Answer Phraser returns the engine summary."""
    monkeypatch.setattr(
        "main.answer_phraser.phrase",
        lambda result, client: f"PHRASED: {result.summary}",
    )


def test_guidance_two_missed_week1_is_moderate_and_phrased():
    response = client.post("/api/guidance", json=_parsed(pillsMissed=2, cycleWeek=1))
    assert response.status_code == 200
    body = response.json()
    assert body["guidance"]["riskLevel"] == "moderate"
    assert body["guidance"]["useBackup"] is True
    assert body["message"].startswith("PHRASED:")


def test_guidance_no_pills_missed_is_no_risk():
    response = client.post("/api/guidance", json=_parsed(pillsMissed=0))
    assert response.status_code == 200
    assert response.json()["guidance"]["riskLevel"] == "none"


def test_guidance_missing_product_returns_422():
    response = client.post("/api/guidance", json=_parsed(product=None))
    assert response.status_code == 422
    assert "product" in response.json()["detail"].lower()


def test_guidance_missing_cycle_week_returns_422():
    response = client.post("/api/guidance", json=_parsed(cycleWeek=None))
    assert response.status_code == 422
    assert "week" in response.json()["detail"].lower()


def test_guidance_invalid_cycle_week_returns_422():
    # cycleWeek out of the engine's 1-4 range -> validation error.
    response = client.post("/api/guidance", json=_parsed(cycleWeek=9))
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# /api/safety-filter
# --------------------------------------------------------------------------- #
def test_safety_filter_flags_week1_multiple_missed_as_urgent():
    response = client.post("/api/safety-filter", json=_parsed(pillsMissed=2, cycleWeek=1))
    assert response.status_code == 200
    body = response.json()
    assert body["urgent"] is True
    assert len(body["triggers"]) >= 1
    assert "emergency" in body["message"].lower()


def test_safety_filter_flags_three_or_more_missed_any_week():
    response = client.post("/api/safety-filter", json=_parsed(pillsMissed=3, cycleWeek=2))
    assert response.json()["urgent"] is True


def test_safety_filter_flags_very_late_pill():
    response = client.post("/api/safety-filter", json=_parsed(pillsMissed=0, hoursLate=80))
    assert response.json()["urgent"] is True


def test_safety_filter_no_flags_for_minor_lapse():
    response = client.post("/api/safety-filter", json=_parsed(pillsMissed=1, cycleWeek=2))
    body = response.json()
    assert body["urgent"] is False
    assert body["triggers"] == []
