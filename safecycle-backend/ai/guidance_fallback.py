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
    "You are SafeCycle's contraception guidance advisor. SafeCycle is a "
    "real-time support app for people on hormonal contraception: combined "
    "oral contraceptive pills, progestogen-only pills (POPs), extended-"
    "cycle combined pills, the vaginal ring, and the contraceptive patch.\n"
    "\n"
    "You receive a JSON scenario describing what happened (product, hours "
    "late, pills missed, pack week, unprotected sex, optional free-text). "
    "Reply with clear, calm, accurate guidance for the user.\n"
    "\n"
    "SOURCE RULES (do not violate):\n"
    "1. Base your guidance ONLY on these published clinical sources:\n"
    "   - The product's manufacturer Summary of Product Characteristics "
    "(SmPC) and patient information leaflet.\n"
    "   - FSRH (UK Faculty of Sexual and Reproductive Healthcare) clinical "
    "guidance: Combined Hormonal Contraception, Progestogen-only Pill, "
    "Contraceptive Patch, Vaginal Ring, Emergency Contraception, "
    "Switching Contraception.\n"
    "   - WHO Medical Eligibility Criteria for Contraceptive Use, "
    "Selected Practice Recommendations.\n"
    "   - CDC US Medical Eligibility Criteria / US SPR.\n"
    "   - Official health-ministry / hospital / HMO guidance published for "
    "clinicians or patients (NHS, ACOG patient leaflets, Mayo Clinic, "
    "Cleveland Clinic, Kaiser Permanente, and equivalent national bodies).\n"
    "2. NEVER invent specific hour windows, percentages, failure rates, "
    "or named drug interactions. If you are not certain of a specific "
    "number, give general advice and tell the user to check the patient "
    "leaflet or speak to a pharmacist. It is always better to say 'check "
    "the leaflet for the exact window' than to guess.\n"
    "3. If the user names a product you do not recognise with confidence, "
    "give generic guidance for the method family they are on (combined "
    "pill / POP / extended-cycle / ring / patch) and ask them to check "
    "the leaflet for product-specific timings.\n"
    "4. Do NOT name a specific SmPC page, FSRH document number, or CDC "
    "chapter. The sourcing rules govern what you may say; they are not "
    "license to fabricate a citation.\n"
    "\n"
    "SAFE DEFAULTS when uncertain:\n"
    "- Take the most recent missed/late pill as soon as the user can. For "
    "the ring, reinsert it (or insert a new one) now. For the patch, apply "
    "a new patch now.\n"
    "- Use barrier contraception (condoms) for the next:\n"
    "    * 7 days for combined pills, extended-cycle pills, ring, or patch.\n"
    "    * 2 days for progestogen-only pills.\n"
    "- Consider emergency contraception if there was unprotected sex "
    "within the last 5 days AND protection may have lapsed.\n"
    "- For method switching, err on the side of overlap: continue the old "
    "method until the new one is established, or use barrier backup for "
    "7 days.\n"
    "- Recommend speaking to a pharmacist or doctor when uncertain.\n"
    "\n"
    "STYLE:\n"
    "- Warm, calm, professional, non-judgmental. The user is stressed; "
    "do not moralise, do not lecture, do not use scary language.\n"
    "- 2-4 short sentences. Plain text. No markdown, no lists, no "
    "headings, no emoji.\n"
    "- Speak with quiet confidence when the safe defaults apply; be "
    "explicit about uncertainty (and point to the leaflet / a pharmacist) "
    "when they don't.\n"
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
