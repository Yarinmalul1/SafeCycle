"""Tests for the FastAPI routes.

`main` constructs an Anthropic client at import time (which reads
ANTHROPIC_API_KEY from the environment), so we set a dummy key before importing.
No network calls are made by these tests — `/health` is fully local, and we
don't exercise the LLM-backed parse endpoint here.
"""

from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

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
