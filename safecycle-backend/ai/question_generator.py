"""Question Generator role.

When a parsed scenario is missing information the logic engine needs (e.g. which
week of the pack the user is in), this role produces a single, clear follow-up
question to ask the user.

NOTE: skeleton — not yet implemented.
"""

from __future__ import annotations

from models import ParsedScenario


def next_question(scenario: ParsedScenario) -> str | None:
    """Return the most useful clarifying question, or None if none needed.

    Args:
        scenario: The (possibly incomplete) parsed scenario.

    Returns:
        A single question string, or None when enough is known to proceed.
    """
    raise NotImplementedError("Question generation is not yet implemented.")
