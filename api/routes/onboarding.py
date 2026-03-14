"""
api/routes/onboarding.py
GET  /onboarding  — serves the HTML signup form
POST /clinic/register — creates a clinic and returns the embed snippet
"""

import os
import secrets
import re
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from core.clinic_store import insert_clinic, get_clinic_by_email
from core.email_client import send_welcome_email
from core.scraper import scrape_website, extract_hours_hint
from core.auth import hash_password

router = APIRouter()


def _make_clinic_id(name: str) -> str:
    """Turn 'Sunshine Dental NYC' → 'sunshine-dental-nyc'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    suffix = secrets.token_hex(3)   # 6-char hex to avoid collisions
    return f"{slug}-{suffix}"


def _make_widget_key() -> str:
    return "pub_" + secrets.token_urlsafe(16)


def _base_url(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    # Railway terminates TLS at the proxy — force https for the embed snippet
    if base.startswith("http://") and "railway.app" in base:
        base = "https://" + base[len("http://"):]
    return base


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_form():
    """Serve the clinic signup form."""
    return HTMLResponse(content=_FORM_HTML)


@router.post("/clinic/register", response_class=HTMLResponse)
async def register_clinic(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    website: str = Form(""),
    allowed_domain: str = Form(...),
    hours: str = Form(""),
    services: str = Form(""),
    faqs: str = Form(""),
    custom_notes: str = Form(""),
    password: str = Form(...),
    plan: str = Form("chatbot"),
):
    # Block duplicate registrations
    if get_clinic_by_email(email.lower().strip()):
        return HTMLResponse(content=_FORM_HTML.replace(
            '<form method="post" action="/clinic/register">',
            '<p style="color:#e53e3e;font-weight:600;margin-bottom:16px;">An account with that email already exists. Please <a href="/portal/login" style="color:#2563eb;">log in</a> instead.</p><form method="post" action="/clinic/register">'
        ))

    clinic_id  = _make_clinic_id(name)
    widget_key = _make_widget_key()

    # Auto-scrape the clinic's website if provided
    scraped = scrape_website(website) if website else ""

    # Auto-detect hours from scrape if clinic left the field blank
    if not hours and scraped:
        hours = extract_hours_hint(scraped)

    valid_plans = {"chatbot", "voice", "both"}
    insert_clinic({
        "clinic_id":      clinic_id,
        "widget_key":     widget_key,
        "name":           name,
        "email":          email.lower().strip(),
        "phone":          phone or None,
        "address":        address or None,
        "website":        website or None,
        "allowed_domain": allowed_domain.lower().strip(),
        "hours":          hours or None,
        "services":       services or None,
        "faqs":           faqs or None,
        "custom_notes":   custom_notes or None,
        "scraped_content": scraped or None,
        "password_hash":  hash_password(password),
        "plan":           plan if plan in valid_plans else "chatbot",
    })

    base_url = _base_url(request)
    embed_snippet = f'<script src="{base_url}/widget.js?key={widget_key}"></script>'

    # Fire welcome email (best-effort — don't crash if email fails)
    try:
        send_welcome_email(name, email, widget_key, base_url)
    except Exception:
        pass

    return HTMLResponse(content=_success_html(name, embed_snippet))


# ---------------------------------------------------------------------------
# HTML templates (inline — no template engine needed for now)
# ---------------------------------------------------------------------------

_FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Set Up Your Dental Chatbot</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #f4f6f8; color: #1a1a2e; }
    .container { max-width: 640px; margin: 48px auto; background: #fff;
                 border-radius: 12px; padding: 40px; box-shadow: 0 2px 16px rgba(0,0,0,.08); }
    h1 { font-size: 1.6rem; margin-bottom: 8px; }
    .subtitle { color: #555; margin-bottom: 32px; font-size: .95rem; }
    label { display: block; font-size: .85rem; font-weight: 600;
            color: #333; margin-bottom: 4px; margin-top: 20px; }
    input, textarea { width: 100%; padding: 10px 12px; border: 1px solid #d0d5dd;
                      border-radius: 8px; font-size: .95rem; font-family: inherit; }
    textarea { resize: vertical; min-height: 80px; }
    .required { color: #e53e3e; }
    .hint { font-size: .78rem; color: #777; margin-top: 4px; }
    button { margin-top: 32px; width: 100%; padding: 14px;
             background: #2563eb; color: #fff; border: none;
             border-radius: 8px; font-size: 1rem; font-weight: 600;
             cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .section-title { font-size: .75rem; font-weight: 700; color: #888;
                     text-transform: uppercase; letter-spacing: .08em;
                     margin-top: 32px; margin-bottom: -4px; }
    .plan-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 14px; }
    .plan-option input[type=radio] { display: none; }
    .plan-option label { display: block; border: 2px solid #d0d5dd; border-radius: 10px;
                         padding: 16px 12px; cursor: pointer; text-align: center;
                         transition: border-color .15s, background .15s; }
    .plan-option input:checked + label { border-color: #2563eb; background: #eff6ff; }
    .plan-option label:hover { border-color: #93c5fd; }
    .plan-name { font-weight: 700; font-size: .95rem; margin-bottom: 4px; }
    .plan-price { font-size: .82rem; color: #2563eb; font-weight: 600; }
    .plan-desc { font-size: .75rem; color: #64748b; margin-top: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Set Up Your AI Chatbot</h1>
    <p class="subtitle">Fill in your clinic's details and we'll generate a chat widget you can add to your website in seconds.</p>

    <form method="post" action="/clinic/register">

      <p class="section-title">Choose Your Plan</p>
      <div class="plan-grid">
        <div class="plan-option">
          <input type="radio" name="plan" id="plan-chatbot" value="chatbot" checked>
          <label for="plan-chatbot">
            <div class="plan-name">Chatbot Only</div>
            <div class="plan-price">$350/mo</div>
            <div class="plan-desc">AI chat widget on your website</div>
          </label>
        </div>
        <div class="plan-option">
          <input type="radio" name="plan" id="plan-voice" value="voice">
          <label for="plan-voice">
            <div class="plan-name">AI Receptionist Only</div>
            <div class="plan-price">$400/mo</div>
            <div class="plan-desc">AI answers missed calls & captures leads</div>
          </label>
        </div>
        <div class="plan-option">
          <input type="radio" name="plan" id="plan-both" value="both">
          <label for="plan-both">
            <div class="plan-name">Chatbot + AI Receptionist</div>
            <div class="plan-price">$550/mo</div>
            <div class="plan-desc">Full AI coverage — chat & phone</div>
          </label>
        </div>
      </div>
      <p class="hint">All plans include a $400 one-time setup fee.</p>

      <p class="section-title">Clinic Basics</p>

      <label>Clinic Name <span class="required">*</span></label>
      <input type="text" name="name" placeholder="Sunshine Dental NYC" required>

      <label>Contact Email <span class="required">*</span></label>
      <input type="email" name="email" placeholder="hello@sunshinedentalnyc.com" required>
      <p class="hint">We'll send your embed code here.</p>

      <label>Password <span class="required">*</span></label>
      <input type="password" name="password" placeholder="Choose a password for your clinic portal" required>
      <p class="hint">You'll use this to log in and view your leads. Make sure it's something you'll remember.</p>

      <label>Phone Number</label>
      <input type="tel" name="phone" placeholder="(212) 555-0100">

      <label>Address</label>
      <input type="text" name="address" placeholder="123 Main St, New York, NY 10001">

      <label>Website URL</label>
      <input type="url" name="website" placeholder="https://sunshinedentalnyc.com">

      <label>Allowed Website Domain <span class="required">*</span></label>
      <input type="text" name="allowed_domain" placeholder="sunshinedentalnyc.com" required>
      <p class="hint">The domain where the widget will be embedded (no https://, no www). This keeps your chatbot from being used on other websites.</p>

      <p class="section-title">What Should the Chatbot Know?</p>

      <label>Hours of Operation</label>
      <textarea name="hours" placeholder="Mon–Fri 9am–5pm, Sat 9am–1pm, closed Sunday"></textarea>

      <label>Services Offered</label>
      <textarea name="services" placeholder="General cleanings, fillings, teeth whitening, Invisalign, implants, emergency care..."></textarea>

      <label>Common Questions & Answers</label>
      <textarea name="faqs" placeholder="Do you accept insurance? Yes, we accept most major plans. Is parking available? Yes, free lot behind the building..."></textarea>

      <label>Anything Else the AI Should Know</label>
      <textarea name="custom_notes" placeholder="We specialize in anxious patients. We do not offer same-day implants. Dr. Smith speaks Spanish..."></textarea>

      <button type="submit">Generate My Chatbot →</button>
    </form>
  </div>
</body>
</html>
"""


def _success_html(clinic_name: str, embed_snippet: str) -> str:
    import html as _html
    escaped = _html.escape(embed_snippet)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Chatbot is Ready</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f4f6f8; color: #1a1a2e; }}
    .container {{ max-width: 640px; margin: 48px auto; background: #fff;
                 border-radius: 12px; padding: 40px; box-shadow: 0 2px 16px rgba(0,0,0,.08); }}
    h1 {{ font-size: 1.6rem; margin-bottom: 8px; }}
    .subtitle {{ color: #555; margin-bottom: 32px; font-size: .95rem; }}
    .code-box {{ background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
                 padding: 16px; font-family: monospace; font-size: .85rem;
                 word-break: break-all; margin: 16px 0; position: relative; }}
    .copy-btn {{ margin-top: 8px; padding: 10px 20px; background: #2563eb; color: #fff;
                 border: none; border-radius: 8px; font-size: .9rem; cursor: pointer;
                 font-weight: 600; }}
    .copy-btn:hover {{ background: #1d4ed8; }}
    .step {{ display: flex; gap: 12px; align-items: flex-start; margin-bottom: 16px; }}
    .step-num {{ background: #2563eb; color: #fff; border-radius: 50%;
                 width: 28px; height: 28px; flex-shrink: 0; display: flex;
                 align-items: center; justify-content: center; font-weight: 700;
                 font-size: .85rem; margin-top: 2px; }}
    .steps {{ margin: 24px 0; }}
    h2 {{ font-size: 1rem; margin: 24px 0 12px; }}
    .check {{ color: #16a34a; margin-right: 6px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>&#127881; {clinic_name} is live!</h1>
    <p class="subtitle">Your AI chatbot is ready. Follow the steps below to add it to your website.</p>

    <h2>Your Embed Code</h2>
    <div class="code-box" id="snippet">{escaped}</div>
    <button class="copy-btn" onclick="copySnippet()">Copy Code</button>

    <div class="steps">
      <h2>How to add it to your website</h2>
      <div class="step">
        <div class="step-num">1</div>
        <div>Open your website editor (WordPress, Squarespace, Wix, etc.)</div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div>Find the option to edit your site's HTML or add a custom script</div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div>Paste the code above before the <code>&lt;/body&gt;</code> tag</div>
      </div>
      <div class="step">
        <div class="step-num">4</div>
        <div>Save and publish — the chat widget will appear on your site immediately</div>
      </div>
    </div>

    <p><span class="check">&#10003;</span>We also sent your embed code to your email address.</p>
    <p style="margin-top:16px;"><a href="/portal/login" style="color:#2563eb;font-weight:600;">Go to your clinic dashboard &rarr;</a></p>
  </div>

  <script>
    function copySnippet() {{
      const text = document.getElementById('snippet').innerText;
      navigator.clipboard.writeText(text).then(() => {{
        const btn = document.querySelector('.copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy Code', 2000);
      }});
    }}
  </script>
</body>
</html>
"""
