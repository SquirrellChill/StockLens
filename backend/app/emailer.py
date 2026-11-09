import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("stocklens")


def send_reset_code(to: str, code: str) -> None:
    """Emails the code when SMTP is configured, otherwise prints it to the server console."""
    if not settings.smtp_host:
        log.warning("Password reset code for %s: %s (SMTP not configured, nothing was emailed)", to, code)
        print(f"[StockLens] Password reset code for {to}: {code}", flush=True)
        return
    msg = EmailMessage()
    msg["Subject"] = "Your StockLens verification code"
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(
        f"Your StockLens verification code is {code}.\n"
        f"It expires in {settings.reset_ttl_minutes} minutes. If you didn't ask for it, ignore this email."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:  # never reveal delivery problems to the caller (no account enumeration)
        log.exception("Could not send reset email to %s", to)
