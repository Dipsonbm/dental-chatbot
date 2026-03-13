"""
core/claude_client.py
Multi-tenant AI chat wrapper — uses Groq (free tier) with Llama 3.1 70B.
Calls the AI, parses the LEAD: marker, and returns (reply, lead_or_None).
"""

import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).parent.parent / ".env")

MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Matches:  LEAD: {"name":"...","phone":"...","email":"...","interest":"..."}
_LEAD_RE = re.compile(r"LEAD:\s*(\{.*?\})", re.DOTALL)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
        "Content-Type": "application/json",
    }


def chat(
    system_prompt: str,
    history: list[dict],
    user_message: str,
) -> tuple[str, dict | None]:
    """
    Send a message to Groq and return (visible_reply, lead_or_None).
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    resp = requests.post(
        GROQ_URL,
        headers=_headers(),
        json={"model": MODEL, "messages": messages, "max_tokens": 1024},
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"] or ""

    # Parse and strip LEAD: marker
    lead = None
    match = _LEAD_RE.search(raw)
    if match:
        try:
            lead = json.loads(match.group(1))
        except json.JSONDecodeError:
            lead = None
        raw = _LEAD_RE.sub("", raw).strip()

    return raw, lead
