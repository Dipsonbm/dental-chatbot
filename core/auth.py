"""
core/auth.py
Password hashing and session management.
Uses built-in hashlib (no extra dependencies).
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta

import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

SESSION_TTL_DAYS = 30


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
# Password hashing  (PBKDF2-SHA256, 100k iterations)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session(clinic_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    ).isoformat()
    requests.post(
        _url("sessions"),
        headers=_headers(),
        json={"token": token, "clinic_id": clinic_id, "expires_at": expires_at},
    )
    return token


def get_session_clinic_id(token: str) -> str | None:
    now = datetime.now(timezone.utc).isoformat()
    resp = requests.get(
        _url("sessions"),
        headers=_headers(),
        params={
            "token": f"eq.{token}",
            "expires_at": f"gt.{now}",
            "select": "clinic_id",
            "limit": "1",
        },
    )
    rows = resp.json()
    if isinstance(rows, list) and rows:
        return rows[0]["clinic_id"]
    return None


def delete_session(token: str) -> None:
    requests.delete(
        _url("sessions"),
        headers=_headers(),
        params={"token": f"eq.{token}"},
    )
