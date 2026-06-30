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
DEFAULT_MODEL = "claude-opus-4-7"

# Mandatory tail appended to every fallback message. The fallback is not a
# clinically-reviewed rule, so users must always see that this is AI-assisted
# guidance and that medical concerns belong with a pharmacist or doctor.
DISCLAIMER = (
    "This is AI-assisted guidance. For medical concerns, consult a pharmacist "
    "or doctor."
)

# System prompt for the Claude fallback. Rewritten to be explicit about (1) the
# kinds of contraception we support, (2) which sources are acceptable, and
# (3) the conservative defaults to fall back on. The goal is reliable, non-
# alarming guidance for any contraception scenario the user describes,
# including ones the deterministic engine doesn't have a rule for.
FALLBACK_SYSTEM = (
    "You are SafeCycle's contraception guidance advisor. SafeCycle is a real-"
    "time support app for people on hormonal contraception: combined oral "
    "contraceptive pills, progestogen-only pills (POPs), extended-cycle "
    "pills, the vaginal ring, and the contraceptive patch.\n"
    "\n"
    "You receive a JSON scenario describing what happened (product, hours "
    "late, pills missed, pack week, unprotected sex, optional free-text). "
    "Reply with clear, calm, accurate guidance for the user.\n"
    "\n"
    "SOURCE RULES (very important):\n"
    "1. Base your guidance ONLY on these published sources:\n"
    "   - The product's manufacturer Summary of Product Characteristics "
    "(SmPC) and patient information leaflet.\n"
    "   - FSRH (UK Faculty of Sexual and Reproductive Healthcare) clinical "
    "guidance: Combined Hormonal Contraception, Progestogen-only Pill, "
    "Contraceptive Patch, Vaginal Ring, Emergency Contraception.\n"
    "   - WHO Medical Eligibility Criteria for Contraceptive Use, Selected "
    "Practice Recommendations.\n"
    "   - CDC US Medical Eligibility Criteria / US SPR.\n"
    "   - Official health-ministry guidance (NHS, etc.).\n"
    "2. Never invent specific hour windows, percentages, or named drug "
    "interactions. If you are not certain about a specific number, give "
    "general advice and tell the user to check the patient leaflet or speak "
    "to a pharmacist.\n"
    "3. If the user names a product you don't recognise with confidence, "
    "give generic guidance for its method family (combined pill / POP / "
    "ring / patch) and ask them to check the leaflet for product-specific "
    "timings.\n"
    "\n"
    "SAFE DEFAULTS when uncertain:\n"
    "- Take the most recent missed/late pill as soon as the user can.\n"
    "- Use barrier contraception (condoms) for the next 7 days for combined "
    "methods, or 2 days for progestogen-only pills.\n"
    "- Consider emergency contraception if there was unprotected sex within "
    "the last 5 days and protection may have lapsed.\n"
    "- Recommend speaking to a pharmacist or doctor.\n"
    "\n"
    "STYLE:\n"
    "- Warm, calm, non-judgmental. The user is stressed; do not moralise.\n"
    "- 2-4 short sentences. Plain text. No markdown, no lists, no headings.\n"
    f"- Always end with this exact sentence: '{DISCLAIMER}'"
)

# Used when Claude cannot be reached. Neutral, conservative, and specifically
# avoids "no rules" / "unsupported" language that users read as the app being
# broken.
SAFE_DEFAULT = (
    "For your situation, the safest next step is to use barrier protection "
    "such as condoms for the next 7 days and speak to a pharmacist or your "
    "doctor. They can give you advice that fits your specific contraception "
    f"and circumstances. {DISCLAIMER}"
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
