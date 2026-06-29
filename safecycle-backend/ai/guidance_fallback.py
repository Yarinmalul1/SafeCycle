"""Claude-backed fallback guidance for unsupported scenarios.

When the deterministic logic engine has no rule set for a user's scenario
(unknown product, novel question, an interaction the rules don't cover yet),
this module asks Claude to generate safe, conservative contraception guidance
instead. The endpoint wraps the resulting text back into the standard
``GuidanceResponse`` shape.

If Claude is unreachable, the function degrades to a static, conservative
message - same pattern as the Answer Phraser - so the endpoint never 5xx's
just because the LLM is down.
"""

from __future__ import annotations

import json

import anthropic

from models import GuidanceResult, ParsedScenario

# Keep in sync with the model default in main.py.
DEFAULT_MODEL = "claude-opus-4-8"

# Mandatory tail appended to every fallback message. The fallback is not a
# clinically-reviewed rule, so users must always see that this is AI-assisted
# guidance and that medical concerns belong with a pharmacist or doctor.
DISCLAIMER = (
    "This is AI-assisted guidance. For medical concerns, consult a pharmacist "
    "or doctor."
)

FALLBACK_SYSTEM = (
    "You are SafeCycle's fallback contraception advisor. The deterministic "
    "rules engine has no rule set for the user's scenario, so they need "
    "general, safe guidance instead of nothing.\n"
    "Rules:\n"
    "- Be calm, warm, and reassuring.\n"
    "- Give conservative, generally-applicable advice. When in doubt, "
    "recommend barrier backup (e.g. condoms) for the next 7 days and speaking "
    "to a pharmacist or doctor.\n"
    "- Do not invent specific timings, percentages, or named drug "
    "interactions that you are not certain about.\n"
    "- Reply in 2-4 sentences. No markdown, no lists, no headings.\n"
    f"- Always end with this exact sentence: '{DISCLAIMER}'"
)

# Used when Claude cannot be reached. Deliberately generic and conservative.
SAFE_DEFAULT = (
    "I don't have specific rules for this scenario yet. To stay safe, use "
    "barrier backup such as condoms for the next 7 days and speak to a "
    f"pharmacist or doctor as soon as you can. {DISCLAIMER}"
)


def fallback_guidance(
    scenario: ParsedScenario,
    engine_result: GuidanceResult | None,
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask Claude for safe fallback guidance.

    Args:
        scenario: The parsed scenario the engine could not handle.
        engine_result: What (if anything) the engine returned before we decided
            to fall back. Passed to Claude as context, may be ``None``.
        client: A configured Anthropic client (reused from the API layer).
        model: Claude model id.

    Returns:
        A short, plain-language message safe to show the user. Falls back to
        :data:`SAFE_DEFAULT` if the LLM call fails.
    """
    payload = {
        "scenario": scenario.model_dump(),
        "engine_result": engine_result.model_dump() if engine_result else None,
    }
    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            system=FALLBACK_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return SAFE_DEFAULT

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    if not text:
        return SAFE_DEFAULT
    # Belt-and-braces: enforce the disclaimer even if the model omitted it.
    if DISCLAIMER not in text:
        text = f"{text} {DISCLAIMER}"
    return text
