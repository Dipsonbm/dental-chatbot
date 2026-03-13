"""
core/leads.py
Save captured patient lead info to the Supabase leads table via REST API.
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


def _url() -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/rest/v1/leads"


def save_lead(
    clinic_id: str,
    session_id: str,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    interest: str | None = None,
    message: str | None = None,
) -> dict:
    """Insert a lead row and return the created record."""
    row = {
        "clinic_id": clinic_id,
        "session_id": session_id,
        "name": name or None,
        "phone": phone or None,
        "email": email or None,
        "interest": interest or None,
        "message": message or None,
    }
    resp = requests.post(
        _url(),
        headers={**_headers(), "Prefer": "return=representation"},
        json=row,
    )
    resp.raise_for_status()
    return resp.json()[0]
