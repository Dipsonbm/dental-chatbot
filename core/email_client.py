"""
core/email_client.py
Email sending via Resend API.
Two functions: send_welcome_email() and send_lead_alert().
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import resend

load_dotenv(Path(__file__).parent.parent / ".env")

resend.api_key = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@yourdomain.com")


def send_welcome_email(
    clinic_name: str,
    clinic_email: str,
    widget_key: str,
    base_url: str,
) -> None:
    """
    Send the onboarding welcome email to a newly registered clinic.
    Includes their embed snippet and setup instructions.
    """
    embed_snippet = (
        f'<script src="{base_url}/widget.js?key={widget_key}"></script>'
    )

    body = f"""Hi {clinic_name},

Welcome! Your AI dental chat assistant is ready.

Paste this snippet before the </body> tag on your website:

{embed_snippet}

That's it — the chat widget will appear automatically on your site.

Tips:
- The widget shows as a floating button in the bottom-right corner
- Patients can ask questions, and it will collect their contact info for appointments
- You'll get an email notification each time a patient submits their details

Questions? Reply to this email and we'll help you out.
"""

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": clinic_email,
        "subject": f"Your dental chatbot is live — embed code inside",
        "text": body,
    })


def send_lead_alert(
    clinic_name: str,
    clinic_email: str,
    lead: dict,
) -> None:
    """
    Notify the clinic when a patient has submitted their contact info.
    """
    name     = lead.get("name") or "Unknown"
    phone    = lead.get("phone") or "Not provided"
    email    = lead.get("email") or "Not provided"
    interest = lead.get("interest") or "Not specified"

    body = f"""New patient inquiry for {clinic_name}:

Name:     {name}
Phone:    {phone}
Email:    {email}
Interest: {interest}

Give them a call to confirm their appointment or answer their question.
"""

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": clinic_email,
        "subject": f"New patient inquiry from {name}",
        "text": body,
    })
