"""History Manager role.

Tracks per-user conversation and scenario history so the pipeline can carry
context across turns (e.g. remember the user's product between messages).

NOTE: skeleton — not yet implemented. Will likely sit on top of `db.queries`.
"""

from __future__ import annotations

from models import ParsedScenario


def record(user_id: str, scenario: ParsedScenario) -> None:
    """Persist a scenario for a user."""
    raise NotImplementedError("History recording is not yet implemented.")


def recent(user_id: str, limit: int = 5) -> list[ParsedScenario]:
    """Return the user's most recent scenarios, newest first."""
    raise NotImplementedError("History retrieval is not yet implemented.")
