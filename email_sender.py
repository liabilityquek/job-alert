"""
Email sender — uses Composio's Gmail integration (no SMTP app password needed).
The Gmail account connected to Composio is used automatically.
"""

import os
from composio import ComposioToolSet


def _get_toolset() -> ComposioToolSet:
    api_key = os.getenv("COMPOSIO_API_KEY", "")
    if not api_key:
        raise ValueError("COMPOSIO_API_KEY not set in .env")
    return ComposioToolSet(api_key=api_key)


def send_job_alert(subject: str, html_body: str) -> bool:
    """
    Send the HTML job alert email via Composio's Gmail integration.

    Required env vars:
      COMPOSIO_API_KEY   — from .env (already set)
      EMAIL_RECIPIENTS   — comma-separated recipient addresses

    Returns True on success, False on failure.
    """
    recipients_raw = os.getenv("EMAIL_RECIPIENTS", "")
    if not recipients_raw:
        print("[Sender] ERROR: EMAIL_RECIPIENTS not set in .env")
        return False

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    primary = recipients[0]
    extra = recipients[1:] if len(recipients) > 1 else []

    try:
        toolset = _get_toolset()
        result = toolset.execute_action(
            action="GMAIL_SEND_EMAIL",
            params={
                "recipient_email": primary,
                "extra_recipients": extra,
                "subject": subject,
                "body": html_body,
                "is_html": True,
            },
        )
        # Composio returns a dict with successfull/data keys
        if result and result.get("successfull", result.get("successful", True)):
            print(f"[Sender] Email sent via Composio to: {', '.join(recipients)}")
            return True
        else:
            print(f"[Sender] Composio returned an error: {result}")
            return False
    except Exception as e:
        print(f"[Sender] Composio send failed: {e}")
        return False


def send_test_email() -> bool:
    """Send a simple test email to verify Composio Gmail config works."""
    from datetime import datetime
    subject = f"[TEST] Job Alert System — {datetime.now().strftime('%d %b %Y %H:%M')}"
    html = """<html><body style="font-family:Arial,sans-serif;padding:24px;">
<h2 style="color:#1a3c5e;">&#10003; Job Alert System — Test Email</h2>
<p>Your Composio Gmail integration is working correctly.</p>
<p style="color:#6b7280;font-size:13px;">
  This is a test message from the automated job alert system.
  Real alerts will be sent every 2 days.
</p>
</body></html>"""
    return send_job_alert(subject, html)
