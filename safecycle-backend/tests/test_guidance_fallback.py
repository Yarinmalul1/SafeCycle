"""Unit tests for the Claude fallback module.

These tests exercise ``ai.guidance_fallback.fallback_guidance`` directly with a
mocked Anthropic client, so they cover behaviours the API-level tests can't
see when the function is stubbed out:

- The function returns a ``(GuidanceResult, message)`` tuple - the frontend
  renderer needs the structured result to build steps / backup / timeline.
- Disclaimer is enforced on the message even if the model omits it.
- Graceful degradation to ``SAFE_DEFAULT_GUIDANCE`` + ``SAFE_DEFAULT_MESSAGE``
  when Claude is unreachable or returns an empty response.
"""

from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

from unittest.mock import MagicMock  # noqa: E402

import anthropic  # noqa: E402

from ai import guidance_fallback  # noqa: E402
from ai.guidance_fallback import (  # noqa: E402
    DISCLAIMER,
    SAFE_DEFAULT_GUIDANCE,
    SAFE_DEFAULT_MESSAGE,
    FallbackOutput,
    fallback_guidance,
)
from models import GuidanceResult, ParsedScenario, RiskLevel  # noqa: E402


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


def _client_returning_parsed(payload: FallbackOutput) -> MagicMock:
    """Stub Anthropic client whose messages.parse returns `payload`."""
    client = MagicMock()
    client.messages.parse.return_value = MagicMock(parsed_output=payload)
    return client


def _client_raising(exc: Exception) -> MagicMock:
    client = MagicMock()
    client.messages.parse.side_effect = exc
    return client


def _valid_payload(**overrides) -> FallbackOutput:
    base = dict(
        riskLevel=RiskLevel.MODERATE,
        takePillNow=True,
        useBackup=True,
        backupDays=7,
        considerEmergencyContraception=False,
        skipPlaceboBreak=False,
        summary="Reapply the patch now and use backup for 7 days.",
        notes=["Patches can lose adhesion; check placement daily."],
        message="Reapply a patch now and use condoms for the next 7 days.",
    )
    base.update(overrides)
    return FallbackOutput(**base)


def test_returns_tuple_of_guidance_and_message():
    client = _client_returning_parsed(_valid_payload())
    result = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert isinstance(result, tuple)
    guidance, message = result
    assert isinstance(guidance, GuidanceResult)
    assert isinstance(message, str)


def test_structured_fields_flow_through_to_guidance_result():
    payload = _valid_payload(
        useBackup=True,
        backupDays=7,
        considerEmergencyContraception=True,
        notes=["Note A", "Note B"],
    )
    client = _client_returning_parsed(payload)
    guidance, _ = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert guidance.useBackup is True
    assert guidance.backupDays == 7
    assert guidance.considerEmergencyContraception is True
    assert guidance.notes == ["Note A", "Note B"]


def test_backup_days_zeroed_when_useBackup_false():
    # Guard against the model saying "no backup needed" but also emitting a
    # non-zero backupDays. The frontend would then render a bogus timeline
    # row. We normalise this at the boundary.
    payload = _valid_payload(useBackup=False, backupDays=7)
    client = _client_returning_parsed(payload)
    guidance, _ = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert guidance.useBackup is False
    assert guidance.backupDays == 0


def test_disclaimer_appended_when_model_omits_it():
    payload = _valid_payload(message="Reapply the patch and use backup for 7 days.")
    client = _client_returning_parsed(payload)
    _, message = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert DISCLAIMER in message


def test_disclaimer_not_duplicated_when_model_already_included_it():
    payload = _valid_payload(message=f"Reapply now and use backup. {DISCLAIMER}")
    client = _client_returning_parsed(payload)
    _, message = fallback_guidance(_scenario(), engine_result=None, client=client)
    assert message.count(DISCLAIMER) == 1


def test_returns_safe_default_when_claude_unreachable():
    err = anthropic.APIConnectionError(request=MagicMock())
    client = _client_raising(err)
    guidance, message = fallback_guidance(
        _scenario(), engine_result=None, client=client
    )
    assert guidance == SAFE_DEFAULT_GUIDANCE
    assert message == SAFE_DEFAULT_MESSAGE
    assert DISCLAIMER in message


def test_returns_safe_default_when_claude_returns_no_parsed_output():
    client = MagicMock()
    client.messages.parse.return_value = MagicMock(parsed_output=None)
    guidance, message = fallback_guidance(
        _scenario(), engine_result=None, client=client
    )
    assert guidance == SAFE_DEFAULT_GUIDANCE
    assert message == SAFE_DEFAULT_MESSAGE
