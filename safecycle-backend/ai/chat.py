"""Chat-conversation contraception advisor.

When the user types a free-text question on /entry, they enter a multi-turn
chat conversation instead of the structured Q&A flow. Each turn is a Claude
call that sees the entire conversation so far -- so the assistant can ask
clarifying follow-ups in the same context.

The system prompt mirrors the one in ai/guidance_fallback.py (sourced from
FSRH / WHO / manufacturer SmPCs, no invented timings, sourced safe defaults)
but is tuned for back-and-forth instead of single-shot guidance.
"""

from __future__ import annotations

import anthropic

# Kept in sync with the model default in main.py.
DEFAULT_MODEL = "claude-opus-4-7"

DISCLAIMER = (
    "This is AI-assisted guidance. For medical concerns, consult a pharmacist "
    "or doctor."
)

# System prompt for the chat conversation. Same sourcing rules + safe
# defaults as the fallback prompt, but framed for a back-and-forth.
CHAT_SYSTEM = (
    "You are SafeCycle's contraception guidance advisor in a chat "
    "conversation. SafeCycle is a real-time support app for people on "
    "hormonal contraception: combined oral contraceptive pills, progestogen-"
    "only pills (POPs), extended-cycle pills, the vaginal ring (NuvaRing), "
    "and the contraceptive patch (Evra/Xulane).\n"
    "\n"
    "The user has typed a free-text question. You may ask up to a few short "
    "clarifying questions before giving a final recommendation. Once you "
    "have enough information, give a clear, sourced, conservative answer.\n"
    "\n"
    "SOURCE RULES (very important):\n"
    "1. Base guidance ONLY on these published sources:\n"
    "   - The product's manufacturer Summary of Product Characteristics "
    "(SmPC) and patient information leaflet.\n"
    "   - FSRH (UK Faculty of Sexual and Reproductive Healthcare) clinical "
    "guidance: Combined Hormonal Contraception, Progestogen-only Pill, "
    "Contraceptive Patch, Vaginal Ring, Emergency Contraception, Switching "
    "Contraception.\n"
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
    "- Each reply: at most 3-4 short sentences. Plain text. No markdown, no "
    "lists, no headings.\n"
    "- If you have enough info to give a final answer, do so. Don't keep "
    f"asking follow-ups forever.\n"
    "- When you give a final answer, end with this exact sentence: "
    f"'{DISCLAIMER}'"
)

# Returned when Claude is unreachable. Mirrors guidance_fallback.SAFE_DEFAULT.
SAFE_DEFAULT = (
    "I'm having trouble reaching the AI advisor right now. For now, the "
    "safest next step is to use barrier protection such as condoms for the "
    "next 7 days and speak to a pharmacist or your doctor. They can give "
    "you advice that fits your specific contraception and circumstances. "
    f"{DISCLAIMER}"
)


def respond(
    messages: list[dict[str, str]],
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate the next assistant turn given the full conversation history.

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}.
        client: A configured Anthropic client.
        model: Claude model id.

    Returns:
        The assistant's reply text. Falls back to ``SAFE_DEFAULT`` if Claude
        cannot be reached.
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=600,
            system=CHAT_SYSTEM,
            messages=messages,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return SAFE_DEFAULT

    text = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()
    return text or SAFE_DEFAULT
