# Workflow: Main Chat (Multi-Tenant)

## Objective

Power the AI assistant for any dental clinic on the platform. Each clinic's chatbot is configured from their row in Supabase — no code changes needed to support a new clinic.

---

## Request Flow

```
POST /api/chat
  { widget_key, message, session_id }
       ↓
core/security.py       — validate widget_key, check Origin header
core/clinic_store.py   — load history from messages table
core/prompt_builder.py — build per-clinic system prompt
core/claude_client.py  — call Claude, parse LEAD: marker
core/clinic_store.py   — save user + assistant messages
core/leads.py          — (if lead) save to leads table
core/email_client.py   — (if lead) email clinic
       ↓
return { reply }
```

---

## Decision Logic

Claude handles all decision-making. The system prompt (built by `prompt_builder.py`) instructs it to:

| Patient intent | Claude behavior |
|----------------|-----------------|
| FAQ / general question | Answer from clinic info only |
| Booking / callback request | Collect name + phone + reason, output LEAD: marker |
| Dental emergency | Empathize, direct to call clinic immediately |
| Medical advice request | Decline, suggest calling or visiting |
| Price inquiry | Acknowledge, direct to call office for quote |
| Out of scope | Politely redirect to dental topics |

---

## Lead Capture Signal

When Claude collects name + phone, it outputs:

```
LEAD: {"name":"Jane Smith","phone":"555-1234","email":"","interest":"cleaning"}
```

`claude_client.py` strips this line before returning `reply` to the widget. The lead dict is passed to `core/leads.py` and `core/email_client.py`.

---

## Files Involved

| File | Role |
|------|------|
| [api/routes/chat.py](../api/routes/chat.py) | Orchestrates the full flow |
| [core/security.py](../core/security.py) | widget_key + origin validation |
| [core/clinic_store.py](../core/clinic_store.py) | History load/save |
| [core/prompt_builder.py](../core/prompt_builder.py) | Per-clinic system prompt |
| [core/claude_client.py](../core/claude_client.py) | Claude API + LEAD parsing |
| [core/leads.py](../core/leads.py) | Save lead to Supabase |
| [core/email_client.py](../core/email_client.py) | Send lead alert email |

---

## Adding a New Clinic

No code changes needed. The clinic fills out the form at `/onboarding` and gets their `widget_key`. The chatbot automatically uses their Supabase row as its knowledge base.

---

## Updating a Clinic's Info

Update their row in the Supabase `clinics` table. Changes take effect on the next chat request — no redeploy needed.

---

## Edge Cases

| Situation | Handling |
|-----------|----------|
| widget_key not in DB | 403 returned, widget shows generic error |
| Origin doesn't match allowed_domain | 403 returned |
| Claude fails / timeout | Widget shows fallback: "Something went wrong, please call us" |
| Lead parsing fails (malformed JSON) | Lead silently dropped, reply still shown |
| Email fails | Logged/silenced — does not break chat response |
| Duplicate lead in same session | Saved again (dedup can be added later) |
