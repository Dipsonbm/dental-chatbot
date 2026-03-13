"""
api/routes/chat.py
POST /api/chat — the main chat endpoint consumed by the widget.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.security import resolve_clinic, check_origin
from core.clinic_store import load_history, save_message
from core.prompt_builder import build_system_prompt
from core.claude_client import chat as claude_chat
from core.leads import save_lead
from core.email_client import send_lead_alert

router = APIRouter()


class ChatRequest(BaseModel):
    widget_key: str
    message: str
    session_id: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, request: Request):
    # 1. Resolve clinic from widget_key (raises 403 if invalid)
    clinic = resolve_clinic(payload.widget_key)

    # 2. Check subscription status — inactive clinics get a polite message
    status = (clinic.get("subscription_status") or "inactive")
    if status not in ("active",):
        return JSONResponse(
            {"reply": "This chatbot is currently unavailable. Please contact the clinic directly."},
            status_code=200,
        )

    # 3. Validate request origin against clinic's allowed_domain
    check_origin(request, clinic)

    # 3. Load conversation history from DB (backend is source of truth)
    history = load_history(payload.session_id)

    # 4. Build per-clinic system prompt
    system_prompt = build_system_prompt(clinic)

    # 5. Call Claude — returns (visible_reply, lead_or_None)
    reply, lead = claude_chat(system_prompt, history, payload.message)

    # 6. Persist both sides of the exchange
    save_message(clinic["clinic_id"], payload.session_id, "user", payload.message)
    save_message(clinic["clinic_id"], payload.session_id, "assistant", reply)

    # 7. If a lead was captured, save it and alert the clinic
    if lead:
        try:
            save_lead(
                clinic_id=clinic["clinic_id"],
                session_id=payload.session_id,
                name=lead.get("name"),
                phone=lead.get("phone"),
                email=lead.get("email"),
                interest=lead.get("interest"),
            )
            send_lead_alert(clinic["name"], clinic["email"], lead)
        except Exception:
            pass  # Don't let email/DB errors break the chat response

    return ChatResponse(reply=reply)
