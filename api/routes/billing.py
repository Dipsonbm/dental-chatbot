"""
api/routes/billing.py
Stripe billing integration.
  POST /billing/checkout  — redirect clinic to Stripe Checkout
  POST /billing/webhook   — handle Stripe webhook events
"""

import os
import requests as _req

import stripe
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse

from core.auth import get_session_clinic_id
from core.clinic_store import get_clinic_by_id, update_clinic

router = APIRouter()


def _base_url(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    if base.startswith("http://") and "railway.app" in base:
        base = "https://" + base[len("http://"):]
    return base


def _stripe_client():
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    return stripe


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@router.post("/billing/checkout")
async def create_checkout(request: Request):
    token = request.cookies.get("db_session")
    if not token:
        return RedirectResponse("/portal/login", status_code=303)

    clinic_id = get_session_clinic_id(token)
    if not clinic_id:
        return RedirectResponse("/portal/login", status_code=303)

    clinic = get_clinic_by_id(clinic_id)
    if not clinic:
        return RedirectResponse("/portal/login", status_code=303)

    s = _stripe_client()
    base = _base_url(request)

    session = s.checkout.Session.create(
        mode="subscription",
        customer_email=clinic["email"],
        line_items=[
            {"price": os.environ["STRIPE_SETUP_PRICE_ID"],   "quantity": 1},
            {"price": os.environ["STRIPE_MONTHLY_PRICE_ID"], "quantity": 1},
        ],
        metadata={"clinic_id": clinic_id},
        success_url=base + "/portal/dashboard?paid=1",
        cancel_url=base + "/portal/dashboard?cancelled=1",
    )

    return RedirectResponse(session.url, status_code=303)


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    s = _stripe_client()

    try:
        event = s.Webhook.construct_event(payload, sig, webhook_secret)
    except Exception:
        return JSONResponse({"error": "invalid signature"}, status_code=400)

    etype = event["type"]
    obj   = event["data"]["object"]

    if etype == "checkout.session.completed":
        clinic_id = (obj.get("metadata") or {}).get("clinic_id")
        if clinic_id:
            update_clinic(clinic_id, {
                "stripe_customer_id":     obj.get("customer"),
                "stripe_subscription_id": obj.get("subscription"),
                "subscription_status":    "active",
            })

    elif etype == "invoice.paid":
        _update_by_subscription(obj.get("subscription"), "active")

    elif etype == "invoice.payment_failed":
        _update_by_subscription(obj.get("subscription"), "past_due")

    elif etype == "customer.subscription.deleted":
        _update_by_subscription(obj.get("id"), "inactive")

    return JSONResponse({"ok": True})


def _update_by_subscription(subscription_id: str | None, status: str) -> None:
    if not subscription_id:
        return
    key  = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    base = os.environ["SUPABASE_URL"].rstrip("/")
    hdrs = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }
    r = _req.get(
        f"{base}/rest/v1/clinics",
        headers=hdrs,
        params={
            "stripe_subscription_id": f"eq.{subscription_id}",
            "select": "clinic_id",
            "limit": "1",
        },
    )
    rows = r.json()
    if isinstance(rows, list) and rows:
        update_clinic(rows[0]["clinic_id"], {"subscription_status": status})
