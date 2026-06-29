"""Persistence layer for SafeCycle calendars (Phase 3).

One row per user (unique constraint on user_id). Generating a new schedule
upserts the row, so 'the user's current schedule' is always a single lookup.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from db.users import _get_client


def upsert_for_user(
    *,
    user_id: str,
    product: str,
    start_date: str,
    hour: int,
    schedule_data: list[dict[str, Any]],
) -> dict:
    """Insert or replace the user's current schedule.

    `start_date` is an ISO date string (YYYY-MM-DD). `schedule_data` is the
    materialised list of events from logic.calendar.generate so the frontend
    doesn't need to re-run the generator to render or export.
    """
    client = _get_client()
    payload = {
        "user_id": user_id,
        "product": product,
        "start_date": start_date,
        "hour": hour,
        "schedule_data": schedule_data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = (
        client.table("calendars")
        .upsert(payload, on_conflict="user_id")
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase upsert returned no row for calendars.")
    return response.data[0]


def get_for_user(user_id: str) -> Optional[dict]:
    """Return the user's current schedule row, or None."""
    client = _get_client()
    response = (
        client.table("calendars")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
