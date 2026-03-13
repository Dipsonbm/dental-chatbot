"""
core/clinic_store.py
Supabase CRUD via direct REST API calls (no Supabase Python SDK).
Compatible with any Python version.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).parent.parent / ".env")


def _headers() -> dict:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _url(table: str) -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/rest/v1/{table}"


# ---------------------------------------------------------------------------
# Clinic lookups
# ---------------------------------------------------------------------------

def get_clinic_by_widget_key(widget_key: str) -> dict | None:
    """Return the clinic row for a given widget_key, or None if not found/inactive."""
    resp = requests.get(
        _url("clinics"),
        headers=_headers(),
        params={
            "widget_key": f"eq.{widget_key}",
            "is_active": "eq.true",
            "limit": "1",
        },
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def insert_clinic(clinic: dict) -> dict:
    """Insert a new clinic row and return the created record."""
    resp = requests.post(
        _url("clinics"),
        headers={**_headers(), "Prefer": "return=representation"},
        json=clinic,
    )
    resp.raise_for_status()
    return resp.json()[0]


# ---------------------------------------------------------------------------
# Message history (owned by backend)
# ---------------------------------------------------------------------------

def load_history(session_id: str) -> list[dict]:
    """
    Return all messages for a session as Claude-compatible dicts.
    [{"role": "user"|"assistant", "content": "..."}]
    Ordered oldest → newest.
    """
    resp = requests.get(
        _url("messages"),
        headers=_headers(),
        params={
            "session_id": f"eq.{session_id}",
            "order": "created_at.asc",
            "select": "role,content",
        },
    )
    resp.raise_for_status()
    return resp.json() or []


def save_message(clinic_id: str, session_id: str, role: str, content: str) -> None:
    """Persist a single message to the messages table."""
    resp = requests.post(
        _url("messages"),
        headers=_headers(),
        json={
            "clinic_id": clinic_id,
            "session_id": session_id,
            "role": role,
            "content": content,
        },
    )
    resp.raise_for_status()
