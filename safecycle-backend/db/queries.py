"""Database queries — in-memory implementation.

This is the only module that should talk to the storage backend directly. For
now it keeps everything in a process-local dict so the rest of the app has a
working, stable interface; swapping in a real database later means changing only
this file.

NOTE: state lives in memory and is lost on restart — fine for the demo, not for
production.
"""

from __future__ import annotations

import itertools
from typing import Any

# user_id -> list of stored session records (oldest first).
_STORE: dict[str, list[dict[str, Any]]] = {}
_ids = itertools.count(1)

# user_id -> authenticated user profile (the signed-in session).
_USERS: dict[str, dict[str, Any]] = {}


def save_scenario(user_id: str, session: dict[str, Any]) -> str:
    """Persist a session for a user and return its new id."""
    sid = str(next(_ids))
    _STORE.setdefault(user_id, []).append({"id": sid, **session})
    return sid


def get_scenarios(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return a user's most recent sessions, newest first."""
    items = _STORE.get(user_id, [])
    return list(reversed(items))[:limit]


def save_user(user_id: str, profile: dict[str, Any]) -> str:
    """Persist (or refresh) a signed-in user's session and return the user id."""
    _USERS[user_id] = profile
    return user_id


def get_user(user_id: str) -> dict[str, Any] | None:
    """Return a stored user session, or None if the user is not signed in."""
    return _USERS.get(user_id)


def reset() -> None:
    """Clear all stored data. Intended for tests."""
    _STORE.clear()
    _USERS.clear()
