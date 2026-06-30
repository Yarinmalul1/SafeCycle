"""Persistence layer for SafeCycle chat conversations.

One chat_sessions row per conversation; one chat_messages row per turn. The
backend uses the Supabase service role key (see db.users._get_client) and
filters by user_id in code, so RLS on the tables is defense-in-depth only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.users import _get_client


def create_session(*, user_id: str, summary: str) -> dict:
    """Insert a new chat_sessions row and return it."""
    client = _get_client()
    row = {"user_id": user_id, "summary": summary[:200]}
    response = client.table("chat_sessions").insert(row).execute()
    if not response.data:
        raise RuntimeError("Supabase insert returned no row for chat_sessions.")
    return response.data[0]


def append_message(*, session_id: str, role: str, content: str) -> dict:
    """Insert a single chat_messages row.

    Also bumps chat_sessions.updated_at so the "most recent chat" sort in
    Profile reflects activity, not just creation time.
    """
    client = _get_client()
    row = {"session_id": session_id, "role": role, "content": content}
    response = client.table("chat_messages").insert(row).execute()
    if not response.data:
        raise RuntimeError("Supabase insert returned no row for chat_messages.")
    client.table("chat_sessions").update(
        {"updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", session_id).execute()
    return response.data[0]


def get_session(session_id: str) -> dict | None:
    """Return one chat_sessions row by id, or None."""
    client = _get_client()
    response = (
        client.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_messages(session_id: str) -> list[dict[str, Any]]:
    """Return all messages in a chat session, oldest first."""
    client = _get_client()
    response = (
        client.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return response.data or []


def recent_for_user(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return up to `limit` most recent chat sessions for one user."""
    client = _get_client()
    response = (
        client.table("chat_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def mark_complete(session_id: str) -> None:
    """Flip chat_sessions.complete to true."""
    client = _get_client()
    client.table("chat_sessions").update({"complete": True}).eq("id", session_id).execute()
