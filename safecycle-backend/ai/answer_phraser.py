"""Answer Phraser role.

Turns the logic engine's structured `GuidanceResult` into clear, warm, non-
alarming text for the user. The engine decides *what* to say; this role decides
*how* to say it.

The engine already produces a sound `summary`; this role uses Claude to rephrase
the full structured result into a single, supportive message. If the LLM is
unreachable, we fall back to the engine's own `summary` so the endpoint stays
functional and deterministic in tests / offline.
"""

from __future__ import annotations

import anthropic

from models import GuidanceResult

# Keep in sync with the model default in main.py.
DEFAULT_MODEL = "claude-opus-4-8"

PHRASER_SYSTEM = (
    "You are the Answer Phraser for SafeCycle, a contraception guidance app. "
    "You are given a structured guidance decision (already made by a "
    "deterministic medical rules engine) as JSON. Rephrase it into a single, "
    "warm, calm, plain-language message for the user. Rules:\n"
    "- Do NOT change the decision: keep every action (take pill now, use backup, "
    "backup days, emergency contraception, skip placebo break) exactly as given.\n"
    "- Be reassuring and non-alarming, but clear about what to do.\n"
    "- Keep it short (2-4 sentences). No markdown, no lists, no headings.\n"
    "- Do not add new medical claims beyond what the decision states."
)


def phrase(
    result: GuidanceResult,
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
) -> str:
    """Render a guidance result as user-facing text.

    Args:
        result: The structured decision from the logic engine.
        client: A configured Anthropic client (reused from the API layer).
        model: Model id to use for phrasing.

    Returns:
        A friendly, plain-language message. Falls back to ``result.summary`` if
        the LLM call fails for any reason.
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=400,
            system=PHRASER_SYSTEM,
            messages=[{"role": "user", "content": result.model_dump_json()}],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return result.summary

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    return text or result.summary
