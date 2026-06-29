"""History Manager role.

Tracks per-user guidance sessions so the app can show a user their past results.
Sits on top of `db.queries`, turning typed models into stored records and back.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db import queries
from models import GuidanceResult, PillScenario


def record(
    user_id: str,
    scenario: PillScenario,
    guidance: GuidanceResult,
    message: str,
) -> str:
    """Persist a completed guidance session and return its id."""
    session: dict[str, Any] = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.model_dump(mode="json"),
        "guidance": guidance.model_dump(mode="json"),
        "message": message,
    }
    return queries.save_scenario(user_id, session)


def recent(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the user's most recent guidance sessions, newest first."""
    return queries.get_scenarios(user_id, limit)
