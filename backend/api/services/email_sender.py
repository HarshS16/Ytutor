"""
Email delivery helpers for account security flows.

Production deployments should configure SMTP_* environment variables or
replace this module with a provider-backed implementation. Development can
fall back to server-side logging without exposing reset codes to the browser.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "development").lower()


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def send_password_reset_otp(email: str, otp: str) -> bool:
    """
    Send a password reset code.

    Returns True when delivery was attempted successfully. In development, if
    SMTP is not configured, the code is logged server-side and True is returned.
    In production, missing SMTP config is treated as a delivery failure.
    """
    if not _smtp_configured():
        if APP_ENV == "development":
            logger.info("Password reset OTP for %s: %s", email, otp)
            return True

        logger.error(
            "Password reset requested for %s, but SMTP_HOST/SMTP_FROM are not configured.",
            email,
        )
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    message = EmailMessage()
    message["Subject"] = "Your Ytutor AI password reset code"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "Use this code to reset your Ytutor AI password:\n\n"
        f"{otp}\n\n"
        "This code expires in 10 minutes. If you did not request it, you can ignore this email."
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        logger.info("Password reset OTP sent to %s", email)
        return True
    except Exception as exc:
        logger.error("Failed to send password reset OTP to %s: %s", email, exc, exc_info=True)
        return False
