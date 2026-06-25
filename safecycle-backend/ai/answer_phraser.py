"""Answer Phraser role.

Turns the logic engine's structured `GuidanceResult` into clear, warm, non-
alarming text for the user. The engine decides *what* to say; this role decides
*how* to say it.

NOTE: skeleton — not yet implemented.
"""

from __future__ import annotations

from models import GuidanceResult


def phrase(result: GuidanceResult) -> str:
    """Render a guidance result as user-facing text.

    Args:
        result: The structured decision from the logic engine.

    Returns:
        A friendly, plain-language message.
    """
    raise NotImplementedError("Answer phrasing is not yet implemented.")
