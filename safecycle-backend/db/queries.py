"""Database queries (stubbed).

This is the only module that should talk to the database directly. For now every
function is a stub so the rest of the app can import a stable interface while the
storage backend is chosen.
"""

from __future__ import annotations

from typing import Any


def save_scenario(user_id: str, scenario: dict[str, Any]) -> str:
    """Persist a scenario and return its new id."""
    raise NotImplementedError("DB layer is stubbed.")


def get_scenarios(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent scenarios for a user, newest first."""
    raise NotImplementedError("DB layer is stubbed.")
