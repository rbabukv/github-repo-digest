"""Send HTML digest email via SMTP or sendmail."""

import smtplib
import subprocess
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import EMAIL_FROM, EMAIL_RECIPIENTS

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.intel.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))


def send_digest(subject, html_body, recipients=None):
    """Send an HTML email using SMTP (preferred) or sendmail fallback."""
    recipients = recipients or EMAIL_RECIPIENTS
    if not recipients:
        raise ValueError("No email recipients configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    plain_text = "This email requires an HTML-capable email client."
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Try SMTP first
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        print(f"   Sent via SMTP ({SMTP_HOST}:{SMTP_PORT})")
        return True
    except Exception as smtp_err:
        print(f"   SMTP failed: {smtp_err}")

    # Fallback to sendmail
    sendmail_path = "/usr/sbin/sendmail"
    if os.path.exists(sendmail_path):
        proc = subprocess.run(
            [sendmail_path, "-t", "-oi"],
            input=msg.as_string(),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            print("   Sent via sendmail")
            return True
        raise RuntimeError(f"sendmail failed (exit {proc.returncode}): {proc.stderr}")

    raise RuntimeError(f"No mail transport available. SMTP error: {smtp_err}")
