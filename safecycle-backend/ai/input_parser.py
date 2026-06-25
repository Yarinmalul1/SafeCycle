"""Input Parser role.

Turns a user's free-text description of a contraception scenario into a
structured `ParsedScenario`. This module isolates the parsing prompt + LLM call
so it can be reused by the API layer and tested independently.

NOTE: skeleton — the live implementation currently lives inline in `main.py`
(`/api/parse-input`). This module is the planned home for that logic.
"""

from __future__ import annotations

from models import ParsedScenario

# System prompt for the Input Parser. Keep in sync with main.py until the
# endpoint is migrated to call `parse()` below.
PARSER_SYSTEM = (
    "You are the Input Parser for SafeCycle, a contraception guidance app. "
    "Your only job is to convert the user's free-text description of a "
    "contraception scenario into the structured schema. "
    "Do NOT give medical advice, risk levels, or recommendations — only parse."
)


def parse(user_input: str) -> ParsedScenario:
    """Parse free text into a structured scenario.

    Args:
        user_input: The user's natural-language description.

    Returns:
        A populated `ParsedScenario`.
    """
    raise NotImplementedError("Input parsing is not yet wired up in this module.")
