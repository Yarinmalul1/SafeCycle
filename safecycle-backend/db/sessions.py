"""Persistence layer for SafeCycle guidance sessions (Phase 2).

Wraps the Supabase 'sessions' table behind a small domain-specific API. The
backend uses the service role key (set in db.users._get_client), so RLS on
the sessions table is bypassed -- we filter by user_id manually in code.
"""

from __future__ import annotations

from typing import Any, Optional

from db.users import _get_client


def record(
    user_id: str,
    *,
    input_text: Optional[str],
    product: Optional[str],
    parsed_data: dict[str, Any],
    guidance_result: dict[str, Any],
    message: str,
    source: str,
) -> dict:
    """Insert one session row and return it.

    Raises if Supabase rejects the insert (e.g. user_id doesn't exist in the
    users table -- the FK constraint will fail). Callers should wrap in a
    try/except and decide whether to surface that to the user.
    """
    client = _get_client()
    row = {
        "user_id": user_id,
        "input_text": input_text,
        "product": product,
        "parsed_data": parsed_data,
        "guidance_result": guidance_result,
        "message": message,
        "source": source,
    }
    response = client.table("sessions").insert(row).execute()
    if not response.data:
        raise RuntimeError("Supabase insert returned no row for sessions.")
    return response.data[0]


def recent_for_user(user_id: str, limit: int = 20) -> list[dict]:
    """Return up to `limit` most recent sessions for one user, newest first."""
    client = _get_client()
    response = (
        client.table("sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []
