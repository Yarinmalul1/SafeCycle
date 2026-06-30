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
DEFAULT_MODEL = "claude-opus-4-7"

PHRASER_SYSTEM = (
    "You are the Answer Phraser for SafeCycle, a contraception guidance app. "
    "You receive a structured guidance decision (already made by a "
    "deterministic medical rules engine grounded in FSRH guidance and the "
    "product manufacturer's SmPC) as JSON. Rephrase it into one warm, calm, "
    "plain-language message for the user.\n"
    "\n"
    "STRICT RULES:\n"
    "1. Preserve the decision exactly: every action the engine specified "
    "(take pill now, use backup, backup days, consider emergency "
    "contraception, skip placebo break) MUST appear in your reply.\n"
    "2. Do not introduce new medical claims, hour windows, percentages, or "
    "drug interactions that are not in the decision JSON. The engine is "
    "authoritative; you are only rephrasing.\n"
    "3. Be warm, calm, and non-alarming, but unambiguous about what to do.\n"
    "4. 2-4 short sentences. Plain text. No markdown, no lists, no headings.\n"
    "5. Do not contradict, soften, or omit any action -- if the decision "
    "says 'use backup for 7 days', say so plainly."
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
