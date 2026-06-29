"""Persistence layer for SafeCycle users (Phase 1).

Wraps the Supabase client behind a tiny domain-specific interface so the rest
of the backend never imports ``supabase`` directly. The client is initialised
lazily on first use so importing this module (e.g. during pytest collection)
does not require Supabase env vars to be set.
"""

from __future__ import annotations

import os
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


def _get_client() -> Client:
    """Return the lazily-initialised Supabase service-role client.

    Raises ``RuntimeError`` with a friendly message if the required env vars
    are missing, so the failure surface is one place instead of a TypeError
    deep inside the supabase library.
    """
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the "
                "backend environment (see safecycle-backend/.env)."
            )
        _client = create_client(url, key)
    return _client


def reset_client_for_tests() -> None:
    """Clear the cached client. Tests use this to inject a different config."""
    global _client
    _client = None


def find_or_create(google_id: str, email: str) -> dict:
    """Idempotent sign-in: return the existing row or insert a new one.

    Upserts on the ``google_id`` unique constraint so concurrent sign-ins from
    the same Google account never produce duplicates. The returned dict has
    the table's columns: ``id``, ``google_id``, ``email``, ``created_at``.
    """
    client = _get_client()
    response = (
        client.table("users")
        .upsert(
            {"google_id": google_id, "email": email},
            on_conflict="google_id",
        )
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase upsert returned no row for users.")
    return response.data[0]


def get_by_id(user_id: str) -> Optional[dict]:
    """Return a user row by primary-key id, or None if it doesn't exist."""
    client = _get_client()
    response = (
        client.table("users").select("*").eq("id", user_id).limit(1).execute()
    )
    return response.data[0] if response.data else None
