"""Claude-backed fallback guidance for unsupported scenarios.

When the deterministic logic engine has no rule set for a user's scenario
(unknown product, novel question, an interaction the rules don't cover yet),
this module asks Claude to generate safe, conservative contraception guidance
and returns it as a *structured* ``GuidanceResult`` plus a user-facing text
message.

The structured return is important: the frontend renderer (``adaptGuidance``
in ``frontend/js/api.js`` and ``buildTimeline`` in
``frontend/js/views/result.js``) builds the "What to do", "Backup protection",
and "Your timeline" sections from ``useBackup`` / ``backupDays`` /
``considerEmergencyContraception`` / ``skipPlaceboBreak`` / ``notes`` on the
guidance object. When this module returned only text, patch and unknown-brand
scenarios ended up rendering the engine's generic defaults instead - which
displayed as "Take the most recent missed or late pill" (wrong copy for
patches) and a "No backup needed - you're protected" timeline (dangerously
wrong when a patch was actually missed). Emitting a structured result fixes
both issues without any frontend change.

If Claude is unreachable, the function degrades to a static, conservative
``SAFE_DEFAULT`` (both the structured guidance and the text) so the endpoint
never 5xx's just because the LLM is down.
"""

from __future__ import annotations

import json

import anthropic
from pydantic import BaseModel, Field

from models import GuidanceResult, ParsedScenario, RiskLevel

# Keep in sync with the model default in main.py.
DEFAULT_MODEL = "claude-opus-4-7"

# Mandatory tail appended to every fallback message. The fallback is not a
# clinically-reviewed rule, so users must always see that this is AI-assisted
# guidance and that medical concerns belong with a pharmacist or doctor.
DISCLAIMER = (
    "This is AI-assisted guidance. For medical concerns, consult a pharmacist "
    "or doctor."
)

# System prompt for the Claude fallback. Rewritten so the model emits every
# field the frontend renderer needs - not just a message string. Sources are
# tightened to FSRH / WHO / CDC / FDA / manufacturer SmPC only; NHS and
# hospital/HMO materials have been removed to match the app's approved-source
# list.
FALLBACK_SYSTEM = (
    "You are SafeCycle's contraception guidance advisor. SafeCycle is a "
    "real-time support app for people on hormonal contraception: combined "
    "oral contraceptive pills, progestogen-only pills (POPs), extended-"
    "cycle combined pills, the vaginal ring, and the contraceptive patch. "
    "You receive a JSON scenario (product, hours late, pills / doses "
    "missed, pack week, unprotected sex) and you return a structured "
    "guidance object plus a short user-facing message.\n"
    "\n"
    "SOURCE RULES (do not violate):\n"
    "1. Base every decision ONLY on these published clinical sources:\n"
    "   - The product's manufacturer Summary of Product Characteristics "
    "(SmPC) and patient information leaflet.\n"
    "   - FSRH (UK Faculty of Sexual and Reproductive Healthcare) clinical "
    "guidance: Combined Hormonal Contraception, Progestogen-only Pill, "
    "Contraceptive Patch, Vaginal Ring, Emergency Contraception, "
    "Switching Contraception.\n"
    "   - WHO Medical Eligibility Criteria for Contraceptive Use, "
    "Selected Practice Recommendations.\n"
    "   - CDC US Medical Eligibility Criteria / US SPR.\n"
    "   - FDA prescribing information for the product.\n"
    "2. NEVER invent specific hour windows, percentages, failure rates, "
    "or named drug interactions. If you are not certain of a specific "
    "number, apply the SAFE DEFAULTS below and tell the user to check the "
    "patient leaflet or speak to a pharmacist. It is always better to say "
    "'check the leaflet for the exact window' than to guess.\n"
    "3. If the user names a product you do not recognise with confidence, "
    "give guidance for the method family they are on (combined pill / POP "
    "/ extended-cycle / ring / patch) using SAFE DEFAULTS.\n"
    "4. Do NOT name a specific SmPC page, FSRH document number, CDC "
    "chapter, or FDA label section. Sourcing governs what you may say; "
    "it is not license to fabricate a citation.\n"
    "5. Do NOT cite Google, Wikipedia, blogs, forums, or general web "
    "results. Only the sources listed in rule 1.\n"
    "\n"
    "SAFE DEFAULTS when uncertain:\n"
    "- Take the most recent missed / late pill as soon as the user can. "
    "For the ring, reinsert it (or insert a new one) now. For the patch, "
    "apply a new patch now.\n"
    "- Use barrier contraception (condoms) for the next:\n"
    "    * 7 days for combined pills, extended-cycle pills, ring, or patch.\n"
    "    * 2 days for progestogen-only pills.\n"
    "- Consider emergency contraception if there was unprotected sex "
    "within the last 5 days AND protection may have lapsed.\n"
    "- For a scheduled placebo / patch-free / ring-free week, protection "
    "is maintained if the last 7 active doses were taken correctly.\n"
    "- Recommend speaking to a pharmacist or doctor when uncertain.\n"
    "\n"
    "STRUCTURED OUTPUT (very important):\n"
    "Return a JSON object matching the FallbackOutput schema:\n"
    "- riskLevel: 'none' / 'low' / 'moderate' / 'high'. Use 'high' when "
    "emergency contraception is warranted (unprotected sex + likely lapse). "
    "Use 'moderate' for a clear lapse without EC concern. Use 'low' or "
    "'none' when protection is intact.\n"
    "- takePillNow: true when the user should take / reinsert / reapply "
    "immediately (nearly always true for a missed-dose scenario).\n"
    "- useBackup: true when barrier contraception is needed. Use SAFE "
    "DEFAULTS for backupDays.\n"
    "- backupDays: 7 (combined / extended / ring / patch) or 2 (POP), "
    "matching useBackup. 0 when useBackup is false.\n"
    "- considerEmergencyContraception: true only when the user reported "
    "unprotected sex during a window where protection may have lapsed.\n"
    "- skipPlaceboBreak: true only for a combined pill missed in week 3 "
    "(patch / ring have their own analogous rules; err on false).\n"
    "- summary: one short headline (a single sentence, no more than 140 "
    "characters). This replaces the engine's generic summary at the top "
    "of the result card. Tailor it to the method: e.g. 'Two patch doses "
    "missed - reapply now and use backup for 7 days.'\n"
    "- notes: zero to three short caveats or method-family reminders "
    "(e.g. 'Patches can lose adhesion in humidity - check placement "
    "daily.'). Each note is a full sentence, plain text.\n"
    "- message: 2 to 4 short sentences, warm, calm, professional, plain "
    "text. No markdown, no lists, no headings, no emoji. Always end with "
    f"this exact sentence: '{DISCLAIMER}'\n"
    "\n"
    "TONE:\n"
    "- Warm, calm, non-judgmental. The user is stressed; do not moralise, "
    "do not lecture, do not use scary language.\n"
    "- Speak with quiet confidence when the safe defaults apply. Be "
    "explicit about uncertainty (point to the leaflet / a pharmacist) "
    "when they don't."
)


class FallbackOutput(BaseModel):
    """Structured payload the fallback Claude call returns.

    Mirrors the fields on ``GuidanceResult`` the frontend renderer reads,
    plus a ``message`` string for the phrased user-facing text. Defined
    inline (not in models.py) because it is a fallback-internal wire shape,
    not part of the public API surface.
    """

    riskLevel: RiskLevel = Field(..., description="Overall risk for the scenario.")
    takePillNow: bool = Field(True, description="Take / reinsert / reapply now.")
    useBackup: bool = Field(False, description="Barrier backup needed.")
    backupDays: int = Field(0, ge=0, description="Number of days of backup.")
    considerEmergencyContraception: bool = Field(
        False, description="EC should be considered."
    )
    skipPlaceboBreak: bool = Field(
        False, description="Skip the pill-free / placebo week."
    )
    summary: str = Field(..., description="One-sentence headline for the result card.")
    notes: list[str] = Field(
        default_factory=list, description="Zero to three short caveats."
    )
    message: str = Field(
        ..., description="2-4 sentence user-facing message, ending with disclaimer."
    )


# Static safe defaults, used when Claude is unreachable or returns empty
# output. Mirrors the SAFE_DEFAULTS section of FALLBACK_SYSTEM so the offline
# experience matches what the model would have produced.
SAFE_DEFAULT_MESSAGE = (
    "For your situation, the safest next step is to use barrier protection "
    "such as condoms for the next 7 days and speak to a pharmacist or your "
    "doctor. They can give you advice that fits your specific contraception "
    f"and circumstances. {DISCLAIMER}"
)

SAFE_DEFAULT = SAFE_DEFAULT_MESSAGE  # Backwards-compat alias for tests / callers.

SAFE_DEFAULT_GUIDANCE = GuidanceResult(
    riskLevel=RiskLevel.MODERATE,
    takePillNow=True,
    useBackup=True,
    backupDays=7,
    considerEmergencyContraception=False,
    skipPlaceboBreak=False,
    summary="Use barrier backup and speak to a pharmacist.",
    notes=[
        "Use condoms as backup for the next 7 days.",
        "Check the patient leaflet for product-specific timings.",
    ],
)


def _apply_disclaimer(text: str) -> str:
    """Ensure the disclaimer sentence is present exactly once at the end."""
    text = (text or "").strip()
    if not text:
        return SAFE_DEFAULT_MESSAGE
    if DISCLAIMER not in text:
        return f"{text} {DISCLAIMER}"
    return text


def fallback_guidance(
    scenario: ParsedScenario,
    engine_result: GuidanceResult | None,
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
) -> tuple[GuidanceResult, str]:
    """Ask Claude for structured fallback guidance.

    Args:
        scenario: The parsed scenario the engine could not handle.
        engine_result: What (if anything) the engine returned before we
            decided to fall back. Passed to Claude as context, may be
            ``None``.
        client: A configured Anthropic client (reused from the API layer).
        model: Claude model id.

    Returns:
        A ``(GuidanceResult, message)`` tuple. The GuidanceResult carries
        the structured overrides the frontend renderer needs; the message is
        the user-facing text ending with ``DISCLAIMER``. On any LLM failure,
        returns ``(SAFE_DEFAULT_GUIDANCE, SAFE_DEFAULT_MESSAGE)``.
    """
    payload = {
        "scenario": scenario.model_dump(),
        "engine_result": engine_result.model_dump() if engine_result else None,
    }

    try:
        response = client.messages.parse(
            model=model,
            max_tokens=800,
            system=FALLBACK_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload)}],
            output_format=FallbackOutput,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return SAFE_DEFAULT_GUIDANCE, SAFE_DEFAULT_MESSAGE

    parsed: FallbackOutput | None = getattr(response, "parsed_output", None)
    if parsed is None:
        return SAFE_DEFAULT_GUIDANCE, SAFE_DEFAULT_MESSAGE

    message = _apply_disclaimer(parsed.message)
    guidance = GuidanceResult(
        riskLevel=parsed.riskLevel,
        takePillNow=parsed.takePillNow,
        useBackup=parsed.useBackup,
        backupDays=parsed.backupDays if parsed.useBackup else 0,
        considerEmergencyContraception=parsed.considerEmergencyContraception,
        skipPlaceboBreak=parsed.skipPlaceboBreak,
        summary=parsed.summary,
        notes=list(parsed.notes),
    )
    return guidance, message
