"""Unit tests for the Claude fallback module.

These tests exercise ``ai.guidance_fallback.fallback_guidance`` directly with a
mocked Anthropic client, so they cover behaviours the API-level tests can't
see when the function is stubbed out (disclaimer enforcement and graceful
degradation when Claude is unreachable).
"""

from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

from unittest.mock import MagicMock  # noqa: E402

import anthropic  # noqa: E402

from ai import guidance_fallback  # noqa: E402
from ai.guidance_fallback import DISCLAIMER, SAFE_DEFAULT, fallback_guidance  # noqa: E402
from models import ParsedScenario  # noqa: E402


def _scenario() -> ParsedScenario:
    """A representative ParsedScenario the engine has no rules for."""
    return ParsedScenario(
        product="mystery-pill",
        hoursLate=None,
        pillsMissed=1,
        cycleWeek=None,
        unprotectedSex=None,
        confidence=0.8,
        clarifyingQuestion=None,
    )


def _client_returning(text: str) -> MagicMock:
    """Build a stub Anthropic client whose messages.create returns `text`."""
    client = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    client.messages.create.return_value = MagicMock(content=[text_block])
    return client


def _client_raising(exc: Exception) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = exc
    return client


def test_disclaimer_appended_when_model_omits_it():
    # The system prompt asks the model to include the disclaimer, but if it
    # doesn't, the function must add it itself.
    client = _client_returning("Use barrier backup for the next 7 days.")
    msg = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert DISCLAIMER in msg


def test_disclaimer_not_duplicated_when_model_already_included_it():
    text = f"Use backup for 7 days. {DISCLAIMER}"
    client = _client_returning(text)
    msg = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert msg.count(DISCLAIMER) == 1


def test_returns_safe_default_with_disclaimer_when_claude_unreachable():
    # APIConnectionError is one of the two failure modes the function catches.
    err = anthropic.APIConnectionError(request=MagicMock())
    client = _client_raising(err)
    msg = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert msg == SAFE_DEFAULT
    assert DISCLAIMER in msg


def test_returns_safe_default_when_claude_returns_empty_response():
    # Empty/whitespace-only model output must also fall through to SAFE_DEFAULT.
    client = _client_returning("   ")
    msg = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert msg == SAFE_DEFAULT
