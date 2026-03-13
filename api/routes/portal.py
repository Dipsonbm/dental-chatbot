"""
api/routes/portal.py
Clinic login portal.
  GET  /portal/login      — login form
  POST /portal/login      — verify credentials, set session cookie
  GET  /portal/dashboard  — leads + edit clinic info (requires auth)
  POST /portal/update     — save clinic info changes (requires auth)
  GET  /portal/logout     — clear session, redirect to login
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import hash_password, verify_password, create_session, get_session_clinic_id, delete_session
from core.clinic_store import get_clinic_by_email, get_clinic_by_id, update_clinic, get_leads

router = APIRouter()

ACCENT = "#2563eb"


def _require_auth(request: Request):
    """Return clinic dict if session is valid, else None."""
    token = request.cookies.get("db_session")
    if not token:
        return None
    clinic_id = get_session_clinic_id(token)
    if not clinic_id:
        return None
    return get_clinic_by_id(clinic_id)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.get("/portal/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(_login_html())


@router.post("/portal/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    clinic = get_clinic_by_email(email)
    stored_hash = (clinic or {}).get("password_hash") or ""

    if not clinic or not stored_hash or not verify_password(password, stored_hash):
        return HTMLResponse(_login_html(error="Invalid email or password."))

    token = create_session(clinic["clinic_id"])
    response = RedirectResponse("/portal/dashboard", status_code=303)
    response.set_cookie(
        "db_session", token,
        httponly=True, max_age=SESSION_TTL_DAYS * 86400, samesite="lax",
    )
    return response


SESSION_TTL_DAYS = 30


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/portal/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    clinic = _require_auth(request)
    if not clinic:
        return RedirectResponse("/portal/login", status_code=303)

    leads = get_leads(clinic["clinic_id"])
    return HTMLResponse(_dashboard_html(clinic, leads))


@router.post("/portal/update", response_class=HTMLResponse)
async def update_info(
    request: Request,
    hours: str = Form(""),
    services: str = Form(""),
    faqs: str = Form(""),
    custom_notes: str = Form(""),
):
    clinic = _require_auth(request)
    if not clinic:
        return RedirectResponse("/portal/login", status_code=303)

    update_clinic(clinic["clinic_id"], {
        "hours":        hours or None,
        "services":     services or None,
        "faqs":         faqs or None,
        "custom_notes": custom_notes or None,
    })

    # Reload fresh clinic data for the page
    clinic = get_clinic_by_id(clinic["clinic_id"])
    leads = get_leads(clinic["clinic_id"])
    return HTMLResponse(_dashboard_html(clinic, leads, saved=True))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.get("/portal/logout")
async def logout(request: Request):
    token = request.cookies.get("db_session")
    if token:
        delete_session(token)
    response = RedirectResponse("/portal/login", status_code=303)
    response.delete_cookie("db_session")
    return response


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

_BASE_CSS = f"""
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f4f6f8; color: #1a1a2e; }}
  a {{ color: {ACCENT}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
"""


def _login_html(error: str = "") -> str:
    err_block = f'<p class="error">{error}</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Clinic Login</title>
  <style>
    {_BASE_CSS}
    .container {{ max-width: 420px; margin: 80px auto; background: #fff;
                 border-radius: 12px; padding: 40px; box-shadow: 0 2px 16px rgba(0,0,0,.08); }}
    h1 {{ font-size: 1.5rem; margin-bottom: 6px; }}
    .subtitle {{ color: #555; font-size: .9rem; margin-bottom: 28px; }}
    label {{ display: block; font-size: .85rem; font-weight: 600; color: #333;
             margin-bottom: 4px; margin-top: 18px; }}
    input {{ width: 100%; padding: 10px 12px; border: 1px solid #d0d5dd;
             border-radius: 8px; font-size: .95rem; font-family: inherit; outline: none; }}
    input:focus {{ border-color: {ACCENT}; }}
    button {{ margin-top: 24px; width: 100%; padding: 13px; background: {ACCENT};
              color: #fff; border: none; border-radius: 8px; font-size: 1rem;
              font-weight: 600; cursor: pointer; }}
    button:hover {{ background: #1d4ed8; }}
    .error {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;
              border-radius: 8px; padding: 10px 14px; margin-top: 16px; font-size: .88rem; }}
    .footer {{ text-align: center; margin-top: 20px; font-size: .82rem; color: #888; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Clinic Login</h1>
    <p class="subtitle">Sign in to manage your chatbot and view leads.</p>
    <form method="post" action="/portal/login">
      <label>Email</label>
      <input type="email" name="email" placeholder="hello@yourclinic.com" required autofocus>
      <label>Password</label>
      <input type="password" name="password" placeholder="Your password" required>
      {err_block}
      <button type="submit">Sign In</button>
    </form>
    <p class="footer">Powered by Ars</p>
  </div>
</body>
</html>"""


def _dashboard_html(clinic: dict, leads: list, saved: bool = False) -> str:
    name         = clinic.get("name", "Your Clinic")
    widget_key   = clinic.get("widget_key", "")
    hours        = clinic.get("hours") or ""
    services     = clinic.get("services") or ""
    faqs         = clinic.get("faqs") or ""
    custom_notes = clinic.get("custom_notes") or ""

    embed = f'&lt;script src="https://web-production-83065.up.railway.app/widget.js?key={widget_key}"&gt;&lt;/script&gt;'
    embed_raw = f'<script src="https://web-production-83065.up.railway.app/widget.js?key={widget_key}"></script>'

    saved_banner = '<div class="banner">Changes saved successfully.</div>' if saved else ""

    # Build leads table rows
    if leads:
        rows_html = ""
        for lead in leads:
            date = (lead.get("created_at") or "")[:10]
            rows_html += f"""
            <tr>
              <td>{lead.get("name") or "-"}</td>
              <td>{lead.get("phone") or "-"}</td>
              <td>{lead.get("email") or "-"}</td>
              <td>{lead.get("interest") or "-"}</td>
              <td>{date}</td>
            </tr>"""
        leads_content = f"""
        <div class="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Interest</th><th>Date</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>"""
    else:
        leads_content = '<p class="empty">No leads yet. They will appear here once patients interact with your chatbot.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} — Dashboard</title>
  <style>
    {_BASE_CSS}
    .topbar {{ background: {ACCENT}; color: #fff; padding: 14px 32px;
               display: flex; align-items: center; justify-content: space-between; }}
    .topbar-title {{ font-weight: 700; font-size: 1.05rem; }}
    .topbar-sub {{ font-size: .82rem; opacity: .85; }}
    .topbar a {{ color: rgba(255,255,255,.85); font-size: .88rem; }}
    .topbar a:hover {{ color: #fff; text-decoration: none; }}
    .main {{ max-width: 860px; margin: 32px auto; padding: 0 20px 60px; }}
    .card {{ background: #fff; border-radius: 12px; padding: 28px 32px;
             box-shadow: 0 2px 12px rgba(0,0,0,.07); margin-bottom: 24px; }}
    .card-title {{ font-size: 1rem; font-weight: 700; color: #1a1a2e; margin-bottom: 18px;
                   padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; }}
    .code-box {{ background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
                 padding: 14px 16px; font-family: monospace; font-size: .82rem;
                 word-break: break-all; margin-bottom: 10px; }}
    .copy-btn {{ padding: 9px 18px; background: {ACCENT}; color: #fff; border: none;
                 border-radius: 8px; font-size: .88rem; cursor: pointer; font-weight: 600; }}
    .copy-btn:hover {{ background: #1d4ed8; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .875rem; }}
    thead tr {{ background: #f8fafc; }}
    th {{ text-align: left; padding: 10px 14px; font-size: .78rem; font-weight: 600;
          color: #64748b; text-transform: uppercase; letter-spacing: .05em;
          border-bottom: 1px solid #e2e8f0; }}
    td {{ padding: 11px 14px; border-bottom: 1px solid #f1f5f9; color: #334155; }}
    tr:last-child td {{ border-bottom: none; }}
    .empty {{ color: #94a3b8; font-size: .9rem; }}
    label {{ display: block; font-size: .85rem; font-weight: 600; color: #333;
             margin-bottom: 4px; margin-top: 18px; }}
    textarea {{ width: 100%; padding: 10px 12px; border: 1px solid #d0d5dd;
                border-radius: 8px; font-size: .88rem; font-family: inherit;
                resize: vertical; min-height: 80px; outline: none; }}
    textarea:focus {{ border-color: {ACCENT}; }}
    .save-btn {{ margin-top: 22px; padding: 12px 28px; background: {ACCENT};
                 color: #fff; border: none; border-radius: 8px; font-size: .95rem;
                 font-weight: 600; cursor: pointer; }}
    .save-btn:hover {{ background: #1d4ed8; }}
    .banner {{ background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0;
               border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; font-size: .9rem; }}
  </style>
</head>
<body>
  <div class="topbar">
    <div>
      <div class="topbar-title">{name}</div>
      <div class="topbar-sub">Clinic Dashboard</div>
    </div>
    <a href="/portal/logout">Sign Out</a>
  </div>

  <div class="main">
    {saved_banner}

    <div class="card">
      <div class="card-title">Your Embed Code</div>
      <div class="code-box" id="embed-snippet">{embed}</div>
      <button class="copy-btn" onclick="copyEmbed()">Copy Code</button>
    </div>

    <div class="card">
      <div class="card-title">Recent Leads</div>
      {leads_content}
    </div>

    <div class="card">
      <div class="card-title">Edit Clinic Info</div>
      <form method="post" action="/portal/update">
        <label>Hours of Operation</label>
        <textarea name="hours" placeholder="Mon-Fri 9am-5pm, Sat 9am-1pm">{hours}</textarea>

        <label>Services Offered</label>
        <textarea name="services" placeholder="Cleanings, fillings, whitening...">{services}</textarea>

        <label>Common Questions &amp; Answers</label>
        <textarea name="faqs" placeholder="Do you accept insurance? Yes...">{faqs}</textarea>

        <label>Additional Notes for the AI</label>
        <textarea name="custom_notes" placeholder="Special instructions for the chatbot...">{custom_notes}</textarea>

        <button type="submit" class="save-btn">Save Changes</button>
      </form>
    </div>
  </div>

  <script>
    function copyEmbed() {{
      const raw = `{embed_raw}`;
      navigator.clipboard.writeText(raw).then(() => {{
        const btn = document.querySelector('.copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy Code', 2000);
      }});
    }}
  </script>
</body>
</html>"""
