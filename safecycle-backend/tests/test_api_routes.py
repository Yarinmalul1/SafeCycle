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


@pytest.fixture(autouse=True)
def _stub_fallback(monkeypatch):
    """Avoid real LLM calls in the Claude fallback path."""
    monkeypatch.setattr(
        "main.guidance_fallback.fallback_guidance",
        lambda scenario, engine_result, client: "FALLBACK: AI-generated guidance.",
    )


@pytest.fixture(autouse=True)
def _reset_history():
    """Each test starts with an empty in-memory history store."""
    from db import queries

    queries.reset()
    yield
    queries.reset()


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


def test_guidance_unprotected_sex_week1_is_high_risk():
    # Two missed in week 1 + unprotected sex -> high risk, emergency contraception.
    response = client.post(
        "/api/guidance",
        json=_parsed(pillsMissed=2, cycleWeek=1, unprotectedSex=True),
    )
    assert response.status_code == 200
    guidance = response.json()["guidance"]
    assert guidance["riskLevel"] == "high"
    assert guidance["considerEmergencyContraception"] is True


def test_guidance_without_unprotected_sex_is_not_high_risk():
    # Same scenario but unprotectedSex not reported -> defaults to no, moderate.
    response = client.post("/api/guidance", json=_parsed(pillsMissed=2, cycleWeek=1))
    guidance = response.json()["guidance"]
    assert guidance["riskLevel"] == "moderate"
    assert guidance["considerEmergencyContraception"] is False


def test_guidance_missing_product_returns_422():
    response = client.post("/api/guidance", json=_parsed(product=None))
    assert response.status_code == 422
    assert "product" in response.json()["detail"].lower()


def test_guidance_missing_cycle_week_for_combined_pill_returns_422():
    # Combined pills (yasmin) still require cycleWeek — their rules branch on it.
    response = client.post("/api/guidance", json=_parsed(cycleWeek=None))
    assert response.status_code == 422
    assert "week" in response.json()["detail"].lower()


def test_guidance_invalid_cycle_week_returns_422():
    # cycleWeek out of the engine's 1-4 range -> validation error.
    response = client.post("/api/guidance", json=_parsed(cycleWeek=9))
    assert response.status_code == 422


def test_guidance_progestogen_only_pill_does_not_require_cycle_week():
    # POPs have no pack-week concept; the endpoint must accept cycleWeek=None.
    response = client.post(
        "/api/guidance",
        json=_parsed(product="cerazette", cycleWeek=None, hoursLate=15),
    )
    assert response.status_code == 200
    guidance = response.json()["guidance"]
    # Cerazette has a 12h window; 15h late is past it -> moderate risk + backup.
    assert guidance["riskLevel"] == "moderate"
    assert guidance["useBackup"] is True


def test_guidance_vaginal_ring_does_not_require_cycle_week():
    # The ring has no pack week either; only hoursLate matters.
    response = client.post(
        "/api/guidance",
        json=_parsed(product="nuvaring", cycleWeek=None, hoursLate=50),
    )
    assert response.status_code == 200
    guidance = response.json()["guidance"]
    # >=48h out -> moderate risk + 7 days backup.
    assert guidance["riskLevel"] == "moderate"
    assert guidance["useBackup"] is True
    assert guidance["backupDays"] == 7


def test_guidance_extended_cycle_pill_does_not_require_cycle_week():
    # Extended-cycle pills (seasonique) ignore weekly placebo logic too.
    response = client.post(
        "/api/guidance",
        json=_parsed(product="seasonique", cycleWeek=None, pillsMissed=2),
    )
    assert response.status_code == 200
    assert response.json()["guidance"]["useBackup"] is True


# --------------------------------------------------------------------------- #
# /api/guidance - Claude fallback path
# --------------------------------------------------------------------------- #
def test_guidance_known_product_uses_engine_source():
    # Known product -> engine path -> source="engine".
    response = client.post("/api/guidance", json=_parsed(pillsMissed=1, cycleWeek=2))
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "engine"
    assert body["message"].startswith("PHRASED:")


def test_guidance_unknown_product_triggers_fallback():
    # Unknown product -> Claude fallback -> source="fallback" and the message
    # comes from the fallback (stubbed), not the answer phraser.
    response = client.post(
        "/api/guidance", json=_parsed(product="mystery-pill", cycleWeek=1)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["message"].startswith("FALLBACK:")
    # The engine still returns its conservative "unsupported" result for shape.
    assert "guidance" in body
    assert body["guidance"]["riskLevel"] in {"none", "low", "moderate", "high"}


def test_guidance_fallback_response_has_valid_shape():
    # The fallback path must still satisfy the GuidanceResponse contract so
    # the frontend can render it like any other guidance result.
    response = client.post(
        "/api/guidance", json=_parsed(product="mystery-pill", cycleWeek=1)
    )
    assert response.status_code == 200
    body = response.json()
    assert {"guidance", "message", "source"} <= body.keys()
    assert isinstance(body["message"], str) and body["message"]
    assert body["source"] in {"engine", "fallback"}
    g = body["guidance"]
    assert {
        "riskLevel",
        "takePillNow",
        "useBackup",
        "backupDays",
        "considerEmergencyContraception",
        "skipPlaceboBreak",
        "summary",
        "notes",
    } <= g.keys()


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


# --------------------------------------------------------------------------- #
# /api/ask-question
# --------------------------------------------------------------------------- #
def _ask(intent="I missed a pill", **ctx) -> dict:
    """An AskQuestionRequest body with an empty-ish context, overridable."""
    context = {
        "product": None,
        "cycleWeek": None,
        "pillsMissed": None,
        "hoursLate": None,
        "confidence": 0.5,
        "clarifyingQuestion": None,
    }
    context.update(ctx)
    return {"userIntent": intent, "existingContext": context}


def test_ask_question_asks_for_product_first():
    response = client.post("/api/ask-question", json=_ask())
    assert response.status_code == 200
    body = response.json()
    assert body["fieldToFill"] == "product"
    assert body["questionNumber"] == 1
    assert "pill" in body["question"].lower()


def test_ask_question_asks_for_week_when_product_known():
    response = client.post("/api/ask-question", json=_ask(product="yasmin"))
    body = response.json()
    assert body["fieldToFill"] == "cycleWeek"
    assert body["questionNumber"] == 2


def test_ask_question_asks_for_missed_when_product_and_week_known():
    response = client.post("/api/ask-question", json=_ask(product="yasmin", cycleWeek=2))
    body = response.json()
    assert body["fieldToFill"] == "pillsMissed"
    assert body["questionNumber"] == 3


def test_ask_question_complete_returns_no_question():
    response = client.post(
        "/api/ask-question",
        json=_ask(product="yasmin", cycleWeek=2, pillsMissed=1),
    )
    body = response.json()
    assert body["question"] is None
    assert body["fieldToFill"] is None
    assert body["questionNumber"] == 4


def test_ask_question_hours_late_satisfies_missed_step():
    # hoursLate alone is enough to consider the lapse known.
    response = client.post(
        "/api/ask-question",
        json=_ask(product="yasmin", cycleWeek=2, hoursLate=30),
    )
    assert response.json()["question"] is None


# --------------------------------------------------------------------------- #
# /api/products
# --------------------------------------------------------------------------- #
def test_products_lists_catalog():
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    names = {p["name"] for p in products}
    assert {"yasmin", "yaz", "cerazette"} <= names


def test_products_mark_supported_families():
    response = client.get("/api/products")
    by_name = {p["name"]: p for p in response.json()}
    assert by_name["yasmin"]["type"] == "combined"
    assert by_name["yasmin"]["supported"] is True
    # Progestogen-only pills now have a rule set too.
    assert by_name["cerazette"]["type"] == "progestogen_only"
    assert by_name["cerazette"]["supported"] is True


# --------------------------------------------------------------------------- #
# /api/history
# --------------------------------------------------------------------------- #
def test_history_empty_for_unknown_user():
    response = client.get("/api/history", params={"user_id": "nobody"})
    assert response.status_code == 200
    assert response.json() == []


def test_guidance_records_a_history_session():
    client.post("/api/guidance", json=_parsed(pillsMissed=2, cycleWeek=1),
                params={"user_id": "alice"})

    response = client.get("/api/history", params={"user_id": "alice"})
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    session = sessions[0]
    assert session["scenario"]["product"] == "yasmin"
    assert session["guidance"]["riskLevel"] == "moderate"
    assert session["message"].startswith("PHRASED:")
    assert "id" in session and "createdAt" in session


def test_history_is_newest_first_and_respects_limit():
    for week in (1, 2, 3):
        client.post("/api/guidance", json=_parsed(pillsMissed=2, cycleWeek=week),
                    params={"user_id": "bob"})

    response = client.get("/api/history", params={"user_id": "bob", "limit": 2})
    sessions = response.json()
    assert len(sessions) == 2
    # Newest first: last posted (week 3) comes first.
    assert sessions[0]["scenario"]["cycleWeek"] == 3
    assert sessions[1]["scenario"]["cycleWeek"] == 2


def test_history_is_scoped_per_user():
    client.post("/api/guidance", json=_parsed(), params={"user_id": "carol"})
    response = client.get("/api/history", params={"user_id": "dave"})
    assert response.json() == []


# --------------------------------------------------------------------------- #
# /api/switch-guidance
# --------------------------------------------------------------------------- #
def test_switch_guidance_seamless_is_protected_and_phrased():
    response = client.post(
        "/api/switch-guidance",
        json={
            "fromMethod": "combined_pill",
            "toMethod": "vaginal_ring",
            "gapDays": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guidance"]["riskLevel"] == "none"
    assert body["guidance"]["useBackup"] is False
    assert body["message"].startswith("PHRASED:")


def test_switch_guidance_gap_with_unprotected_sex_is_high_risk():
    response = client.post(
        "/api/switch-guidance",
        json={
            "fromMethod": "progestogen_only_pill",
            "toMethod": "combined_pill",
            "gapDays": 4,
            "unprotectedSex": True,
        },
    )
    assert response.status_code == 200
    guidance = response.json()["guidance"]
    assert guidance["riskLevel"] == "high"
    assert guidance["considerEmergencyContraception"] is True


def test_switch_guidance_rejects_unknown_method():
    response = client.post(
        "/api/switch-guidance",
        json={"fromMethod": "telepathy", "toMethod": "combined_pill"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# /api/auth/google
# --------------------------------------------------------------------------- #
def _fake_id_token(claims: dict) -> str:
    """Build an unsigned JWT-shaped token (header.payload.signature)."""
    import base64
    import json

    def seg(obj: dict) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{seg({'alg': 'none'})}.{seg(claims)}.signature"


def test_auth_google_returns_profile_and_stores_session():
    from db import queries

    token = _fake_id_token(
        {"sub": "1234567890", "email": "sarah@example.com", "name": "Sarah Levi"}
    )
    response = client.post("/api/auth/google", json={"credential": token})

    assert response.status_code == 200
    body = response.json()
    assert body == {"name": "Sarah Levi", "email": "sarah@example.com", "userId": "1234567890"}
    # The session is stored in memory under the stable user id.
    assert queries.get_user("1234567890") == body


def test_auth_google_rejects_malformed_credential():
    response = client.post("/api/auth/google", json={"credential": "not-a-jwt"})
    assert response.status_code == 401
