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

# Disclaimer surfaced when the engine flagged the situation as high risk.
# Only appended in that case - low/none risk phrasings stay short and
# reassuring rather than heavy with a legal-style tail on every reply.
HIGH_RISK_TAIL = (
    "If you're unsure, please speak with a pharmacist or your doctor."
)

PHRASER_SYSTEM = (
    "You are the Answer Phraser for SafeCycle, a contraception guidance app. "
    "You receive a structured guidance decision (already made by a "
    "deterministic medical rules engine) as JSON, and you rephrase it into "
    "one warm, calm, professional message for the user. The engine's "
    "decisions are grounded in published clinical sources - the product's "
    "manufacturer Summary of Product Characteristics (SmPC), FSRH (UK "
    "Faculty of Sexual and Reproductive Healthcare) clinical guidance, WHO "
    "Medical Eligibility Criteria + Selected Practice Recommendations, and "
    "CDC US MEC / SPR - so you can phrase the guidance with quiet "
    "confidence.\n"
    "\n"
    "STRICT RULES (do not violate):\n"
    "1. Preserve the decision exactly. Every action the engine specified "
    "MUST appear in your reply, in plain language the user can act on:\n"
    "   - takePillNow=true  -> tell them to take the most recent missed / "
    "late pill now (or, for the ring, to reinsert it now).\n"
    "   - useBackup=true    -> tell them to use barrier contraception "
    "(condoms) for the exact number of backupDays specified.\n"
    "   - considerEmergencyContraception=true -> tell them to consider "
    "emergency contraception and speak to a pharmacist as soon as they can.\n"
    "   - skipPlaceboBreak=true -> tell them to skip the pill-free / "
    "placebo week and start the next pack straight away.\n"
    "2. Do NOT introduce new medical claims, hour windows, percentages, "
    "drug interactions, or brand-specific timings that are not in the "
    "decision JSON. The engine is authoritative; you are rephrasing, not "
    "diagnosing.\n"
    "3. Do NOT contradict, soften, or omit any action. If the decision says "
    "'use backup for 7 days', say '7 days' - not 'about a week', not 'a few "
    "days', not 'maybe use backup'.\n"
    "4. Do NOT invent citations or name specific documents. The sourcing "
    "framing lets you speak confidently; it does not license quoting a "
    "particular SmPC / FSRH page number.\n"
    "\n"
    "TONE:\n"
    "- Warm, calm, non-judgmental. The user is stressed; do not moralise, "
    "do not lecture, do not use scary language.\n"
    "- Professional but plain - like a good pharmacist explaining next "
    "steps, not a clinical leaflet.\n"
    "- Reassuring when the risk is low ('you're still protected'); "
    "unambiguous when action is needed.\n"
    "\n"
    "FORMAT:\n"
    "- 2-4 short sentences. Plain text only. No markdown, no bullet lists, "
    "no headings, no emoji.\n"
    "- When the decision's riskLevel is 'high', end with this exact "
    f"sentence: '{HIGH_RISK_TAIL}' For 'none' / 'low' / 'moderate', omit "
    "that tail - the app surfaces a global disclaimer separately."
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
