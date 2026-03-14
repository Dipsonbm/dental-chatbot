"""
api/routes/voice.py
Twilio voice bot — AI phone receptionist for dental clinics.
  POST /voice/incoming  — Twilio calls this when a call arrives
  POST /voice/respond   — Twilio calls this after each speech turn
  POST /voice/provision — Dashboard: buy + assign a Twilio number to a clinic
"""

import os

from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response, JSONResponse

from core.auth import get_session_clinic_id
from core.clinic_store import (
    get_clinic_by_phone, get_clinic_by_id, update_clinic,
    load_history, save_message,
)
from core.prompt_builder import build_system_prompt
from core.claude_client import chat as ai_chat
from core.leads import save_lead
from core.email_client import send_lead_alert

router = APIRouter()

BASE_URL = "https://web-production-83065.up.railway.app"
VOICE    = "Polly.Joanna"   # Natural US female voice via Twilio/AWS Polly


def _client() -> Client:
    return Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


def _send_sms_confirmation(clinic: dict, lead: dict) -> None:
    """Send an SMS confirmation to the patient after lead capture."""
    patient_phone = lead.get("phone")
    clinic_phone  = clinic.get("twilio_phone")
    if not patient_phone or not clinic_phone:
        return

    clinic_name = clinic.get("name", "the clinic")
    interest    = lead.get("interest") or "your inquiry"
    name        = lead.get("name") or "there"

    body = (
        f"Hi {name}! Thanks for calling {clinic_name}. "
        f"We've noted your interest in {interest} and will call you back shortly to confirm. "
        f"Questions? Call us at {clinic_phone}."
    )

    _client().messages.create(
        body=body,
        from_=clinic_phone,
        to=patient_phone,
    )


def _xml(resp: VoiceResponse) -> Response:
    return Response(content=str(resp), media_type="application/xml")


# ---------------------------------------------------------------------------
# Incoming call — greet the caller
# ---------------------------------------------------------------------------

@router.post("/voice/incoming")
async def voice_incoming(
    To:      str = Form(""),
    CallSid: str = Form(""),
):
    resp = VoiceResponse()
    clinic = get_clinic_by_phone(To)

    if not clinic:
        resp.say("Sorry, this number is not configured. Please try again later.", voice=VOICE)
        return _xml(resp)

    clinic_name = clinic.get("name", "the clinic")
    action_url  = f"{BASE_URL}/voice/respond?clinic_id={clinic['clinic_id']}&call_sid={CallSid}"

    gather = Gather(input="speech", action=action_url, speech_timeout="auto", timeout=6, language="en-US")
    gather.say(
        f"Hi, thank you for calling {clinic_name}. I'm the AI assistant. How can I help you today?",
        voice=VOICE,
    )
    resp.append(gather)
    # Fallback if caller says nothing
    resp.say("I didn't catch that. Please call back during business hours. Goodbye!", voice=VOICE)
    return _xml(resp)


# ---------------------------------------------------------------------------
# Each speech turn
# ---------------------------------------------------------------------------

@router.post("/voice/respond")
async def voice_respond(
    request:      Request,
    SpeechResult: str = Form(""),
    CallSid:      str = Form(""),
):
    clinic_id = request.query_params.get("clinic_id", "")
    call_sid  = request.query_params.get("call_sid") or CallSid
    action_url = f"{BASE_URL}/voice/respond?clinic_id={clinic_id}&call_sid={call_sid}"

    resp = VoiceResponse()

    if not SpeechResult.strip():
        gather = Gather(input="speech", action=action_url, speech_timeout="auto", timeout=6)
        gather.say("I didn't catch that — could you repeat that?", voice=VOICE)
        resp.append(gather)
        return _xml(resp)

    clinic = get_clinic_by_id(clinic_id)
    if not clinic:
        resp.say("Sorry, something went wrong. Please call back during business hours.", voice=VOICE)
        return _xml(resp)

    # AI response
    history       = load_history(call_sid)
    system_prompt = build_system_prompt(clinic, voice=True)
    reply, lead   = ai_chat(system_prompt, history, SpeechResult)

    # Persist conversation
    save_message(clinic_id, call_sid, "user",      SpeechResult)
    save_message(clinic_id, call_sid, "assistant", reply)

    # Lead capture
    if lead:
        try:
            save_lead(
                clinic_id=clinic_id,
                session_id=call_sid,
                name=lead.get("name"),
                phone=lead.get("phone"),
                email=lead.get("email"),
                interest=lead.get("interest"),
            )
            send_lead_alert(clinic["name"], clinic["email"], lead)
            _send_sms_confirmation(clinic, lead)
        except Exception:
            pass

    # Speak reply then listen again
    gather = Gather(input="speech", action=action_url, speech_timeout="auto", timeout=6)
    gather.say(reply, voice=VOICE)
    resp.append(gather)
    resp.say("Thank you for calling. Have a great day!", voice=VOICE)
    return _xml(resp)


# ---------------------------------------------------------------------------
# Provision a phone number for a clinic (called from dashboard)
# ---------------------------------------------------------------------------

@router.post("/voice/provision")
async def provision_number(request: Request):
    token = request.cookies.get("db_session")
    if not token:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    clinic_id = get_session_clinic_id(token)
    if not clinic_id:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    clinic = get_clinic_by_id(clinic_id)
    if not clinic:
        return JSONResponse({"error": "not found"}, status_code=404)

    # Check plan allows voice
    plan = clinic.get("plan") or "chatbot"
    if plan not in ("voice", "both"):
        return JSONResponse({"error": "Voice is not included in your current plan."}, status_code=403)

    # Already has a number
    if clinic.get("twilio_phone"):
        return JSONResponse({"phone": clinic["twilio_phone"]})

    try:
        client  = _client()
        numbers = client.available_phone_numbers("US").local.list(limit=1)
        if not numbers:
            return JSONResponse({"error": "No numbers available"}, status_code=500)

        purchased = client.incoming_phone_numbers.create(
            phone_number=numbers[0].phone_number,
            voice_url=f"{BASE_URL}/voice/incoming",
            voice_method="POST",
        )
        update_clinic(clinic_id, {"twilio_phone": purchased.phone_number})
        return JSONResponse({"phone": purchased.phone_number})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
