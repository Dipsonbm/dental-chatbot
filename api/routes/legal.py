"""
api/routes/legal.py
Legal pages for Ars AI platform.

GET /terms
GET /privacy
GET /ai-disclaimer
GET /medical-disclaimer
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_STYLE = """
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: #f8fafc; color: #1e293b; }
    header { background: #2563eb; padding: 18px 40px; }
    header a { color: white; text-decoration: none; font-weight: 700; font-size: 1.1rem; }
    .container { max-width: 780px; margin: 48px auto; padding: 0 24px 80px; }
    h1 { font-size: 1.75rem; margin-bottom: 8px; }
    .updated { color: #64748b; font-size: .85rem; margin-bottom: 36px; }
    h2 { font-size: 1.1rem; margin: 32px 0 10px; color: #1e293b; }
    p, li { font-size: .95rem; line-height: 1.7; color: #374151; }
    ul { padding-left: 20px; margin-top: 8px; }
    li { margin-bottom: 6px; }
    a { color: #2563eb; }
    footer { margin-top: 48px; padding-top: 24px; border-top: 1px solid #e2e8f0; font-size: .85rem; color: #94a3b8; }
  </style>
"""

def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Ars AI</title>
  {_STYLE}
</head>
<body>
  <header><a href="/onboarding">Ars AI</a></header>
  <div class="container">
    {body}
    <footer>
      &copy; 2025 Ars AI &nbsp;|&nbsp;
      <a href="/terms">Terms of Service</a> &nbsp;|&nbsp;
      <a href="/privacy">Privacy Policy</a> &nbsp;|&nbsp;
      <a href="/ai-disclaimer">AI Disclaimer</a> &nbsp;|&nbsp;
      <a href="/medical-disclaimer">Medical Disclaimer</a>
    </footer>
  </div>
</body>
</html>"""


@router.get("/terms", response_class=HTMLResponse)
async def terms():
    body = """
    <h1>Terms of Service</h1>
    <p class="updated">Last updated: March 14, 2025</p>

    <h2>1. Agreement</h2>
    <p>By signing up for and using Ars AI ("the Service"), you agree to these Terms of Service. If you do not agree, do not use the Service.</p>

    <h2>2. Description of Service</h2>
    <p>Ars AI provides AI-powered chatbot and voice receptionist software for dental clinics on a subscription basis. The Service enables clinics to capture patient inquiries, provide basic information, and collect lead details automatically.</p>

    <h2>3. Subscription and Billing</h2>
    <ul>
      <li>A one-time setup fee is charged upon registration.</li>
      <li>Monthly subscription fees are billed automatically via Stripe.</li>
      <li>You may cancel your subscription at any time from your clinic dashboard.</li>
      <li>No refunds are issued for partial months already billed.</li>
      <li>Ars AI reserves the right to update pricing with 30 days' notice.</li>
    </ul>

    <h2>4. Acceptable Use</h2>
    <p>You agree not to use the Service to:</p>
    <ul>
      <li>Provide false or misleading information to patients</li>
      <li>Violate any applicable laws or regulations</li>
      <li>Attempt to reverse-engineer or tamper with the platform</li>
      <li>Resell or sublicense access to the Service without written consent</li>
    </ul>

    <h2>5. Data and Privacy</h2>
    <p>Patient conversation data and lead information are stored securely and are accessible only to your clinic. See our <a href="/privacy">Privacy Policy</a> for details.</p>

    <h2>6. Disclaimer of Warranties</h2>
    <p>The Service is provided "as is" without warranties of any kind. Ars AI does not guarantee uninterrupted uptime or that the AI will respond accurately in all situations.</p>

    <h2>7. Limitation of Liability</h2>
    <p>Ars AI shall not be liable for any indirect, incidental, or consequential damages arising from your use of the Service. Our total liability shall not exceed the amount you paid in the 30 days preceding the claim.</p>

    <h2>8. Termination</h2>
    <p>We reserve the right to suspend or terminate your account for violation of these terms, with or without notice.</p>

    <h2>9. Contact</h2>
    <p>For questions about these terms, email us at <a href="mailto:arsbuis@gmail.com">arsbuis@gmail.com</a>.</p>
    """
    return HTMLResponse(_page("Terms of Service", body))


@router.get("/privacy", response_class=HTMLResponse)
async def privacy():
    body = """
    <h1>Privacy Policy</h1>
    <p class="updated">Last updated: March 14, 2025</p>

    <h2>1. Overview</h2>
    <p>Ars AI ("we", "us") is committed to protecting the privacy of clinic owners and their patients. This policy explains what data we collect, how we use it, and how it is protected.</p>

    <h2>2. Data We Collect</h2>
    <p><strong>From clinic owners (during registration):</strong></p>
    <ul>
      <li>Clinic name, email address, phone number, and business address</li>
      <li>Website URL and clinic details (hours, services, FAQs)</li>
      <li>Password (stored as a secure hash — never in plain text)</li>
    </ul>
    <p style="margin-top:12px;"><strong>From patient conversations:</strong></p>
    <ul>
      <li>Chat messages and conversation history</li>
      <li>Lead information voluntarily provided by patients (name, phone, email, appointment interest)</li>
    </ul>

    <h2>3. How We Use Data</h2>
    <ul>
      <li>To operate and deliver the chatbot and voice receptionist service</li>
      <li>To send lead alert emails to the clinic</li>
      <li>To process payments via Stripe</li>
      <li>To send onboarding and account-related emails via Resend</li>
    </ul>

    <h2>4. Third-Party Services</h2>
    <ul>
      <li><strong>Supabase</strong> — secure database storage for clinic and patient data</li>
      <li><strong>Stripe</strong> — payment processing (we do not store card details)</li>
      <li><strong>Twilio</strong> — voice call handling for AI Receptionist plans</li>
      <li><strong>Anthropic</strong> — AI model powering chat and voice responses</li>
      <li><strong>Resend</strong> — transactional email delivery</li>
    </ul>

    <h2>5. Data Retention</h2>
    <p>Conversation history and lead data are retained for the duration of the clinic's active subscription. Upon cancellation, data may be deleted after 90 days.</p>

    <h2>6. Security</h2>
    <p>All data is transmitted over HTTPS. Passwords are hashed using PBKDF2-SHA256. Database access uses service-role keys and is not publicly exposed.</p>

    <h2>7. Your Rights</h2>
    <p>Clinic owners may request deletion of their account and associated data at any time by contacting us at <a href="mailto:arsbuis@gmail.com">arsbuis@gmail.com</a>.</p>

    <h2>8. Contact</h2>
    <p>For privacy-related questions, email <a href="mailto:arsbuis@gmail.com">arsbuis@gmail.com</a>.</p>
    """
    return HTMLResponse(_page("Privacy Policy", body))


@router.get("/ai-disclaimer", response_class=HTMLResponse)
async def ai_disclaimer():
    body = """
    <h1>AI Disclaimer</h1>
    <p class="updated">Last updated: March 14, 2025</p>

    <h2>This Service Uses Artificial Intelligence</h2>
    <p>The chat widget and voice receptionist on this platform are powered by artificial intelligence. You are not speaking with a human staff member.</p>

    <h2>What the AI Can Do</h2>
    <ul>
      <li>Answer general questions about the clinic's hours, services, and location</li>
      <li>Collect your name, phone number, and appointment interest so a staff member can follow up</li>
      <li>Provide general information based on details supplied by the clinic</li>
    </ul>

    <h2>What the AI Cannot Do</h2>
    <ul>
      <li>Confirm, schedule, or guarantee appointments</li>
      <li>Access real-time availability or booking systems</li>
      <li>Provide accurate medical or dental diagnoses</li>
      <li>Replace the judgment of a licensed dental professional</li>
    </ul>

    <h2>Accuracy</h2>
    <p>While we strive for accuracy, AI responses may occasionally be incomplete or incorrect. Always verify important information directly with the clinic by phone or in person.</p>

    <h2>Follow-Up</h2>
    <p>If you submit your contact information through the chat, a real clinic staff member will follow up with you to confirm your appointment or answer further questions.</p>

    <h2>Contact</h2>
    <p>Questions? Email <a href="mailto:arsbuis@gmail.com">arsbuis@gmail.com</a>.</p>
    """
    return HTMLResponse(_page("AI Disclaimer", body))


@router.get("/medical-disclaimer", response_class=HTMLResponse)
async def medical_disclaimer():
    body = """
    <h1>Medical Disclaimer</h1>
    <p class="updated">Last updated: March 14, 2025</p>

    <h2>Not Medical or Dental Advice</h2>
    <p>The information provided by the Ars AI chatbot and voice receptionist is for <strong>general informational purposes only</strong>. It does not constitute medical or dental advice, diagnosis, or treatment.</p>

    <h2>No Professional Relationship</h2>
    <p>Using this AI service does not create a patient-dentist or patient-doctor relationship. The AI is not a licensed healthcare provider and cannot evaluate your individual health circumstances.</p>

    <h2>Always Consult a Professional</h2>
    <p>Never disregard professional dental or medical advice or delay seeking it because of something you read or heard through this AI service. If you have a dental emergency, pain, or urgent concern, contact your dentist directly or visit an emergency care facility.</p>

    <h2>Emergency Situations</h2>
    <p>If you are experiencing a medical emergency, call <strong>911</strong> or go to your nearest emergency room immediately. Do not rely on this AI service in emergency situations.</p>

    <h2>Limitation of Liability</h2>
    <p>Ars AI and the clinic using this platform are not responsible for any actions taken or not taken based on information provided by the AI assistant.</p>

    <h2>Contact</h2>
    <p>Questions? Email <a href="mailto:arsbuis@gmail.com">arsbuis@gmail.com</a>.</p>
    """
    return HTMLResponse(_page("Medical Disclaimer", body))
