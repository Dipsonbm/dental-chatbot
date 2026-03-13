"""
Tool: ask_claude.py
Purpose: Send a conversation to Claude and get a response.
Used by: All workflows that need AI-generated replies.

Usage:
    python tools/ask_claude.py

    Or import and call ask_claude() directly from other tools/workflows.
"""

import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# Load .env from project root (one level up from tools/)
load_dotenv(Path(__file__).parent.parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-6"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_base" / "clinic_info.md"
WORKFLOW_PATH = Path(__file__).parent.parent / "workflows" / "main_chat.md"


def load_clinic_info() -> str:
    """Load the clinic knowledge base from markdown."""
    if not KNOWLEDGE_BASE_PATH.exists():
        return "[Clinic information not available]"
    return KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8")


def build_system_prompt() -> str:
    """Build the system prompt by injecting clinic info into the template."""
    clinic_info = load_clinic_info()
    current_date = date.today().strftime("%B %d, %Y")

    return f"""You are the AI assistant for a dental clinic's website chat widget. \
You help patients by answering questions about the clinic, booking appointments, \
and making them feel welcome.

Here is everything you need to know about the clinic:

{clinic_info}

Guidelines:
- Be warm, concise, and professional — like a knowledgeable front-desk receptionist
- Answer only from the clinic information provided above — do not invent facts
- For appointment booking, collect details conversationally, one step at a time
- Never provide medical diagnoses or specific treatment advice
- Never quote exact prices — direct patients to call the office
- For dental emergencies (pain, swelling, broken tooth, bleeding), always direct \
patients to call the clinic immediately
- Keep replies short — 2–4 sentences unless the patient needs more detail

Today's date: {current_date}"""


def ask_claude(
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Send a message to Claude and return the response text.

    Args:
        user_message: The patient's latest message.
        conversation_history: List of prior messages in the format
            [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        Claude's response as a plain string.
    """
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_key_here":
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add your key to the .env file."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=build_system_prompt(),
        messages=messages,
    )

    return response.content[0].text


# ---------------------------------------------------------------------------
# Quick test — run this file directly to verify everything is wired up
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing ask_claude.py...")
    print("-" * 40)

    history = []

    test_messages = [
        "Hi! What are your hours?",
        "Do you accept kids?",
        "I'd like to book an appointment.",
    ]

    for msg in test_messages:
        print(f"\nPatient: {msg}")
        reply = ask_claude(msg, history)
        print(f"Assistant: {reply}")
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": reply})

    print("\n" + "-" * 40)
    print("Test complete.")
