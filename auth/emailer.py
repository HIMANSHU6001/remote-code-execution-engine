from __future__ import annotations

import logging
from urllib.parse import quote

import resend  # type: ignore[reportMissingModuleSource]

from config.settings import settings

logger = logging.getLogger(__name__)


def _verification_url(raw_token: str) -> str:
    separator = "&" if "?" in settings.VERIFY_EMAIL_BASE_URL else "?"
    return f"{settings.VERIFY_EMAIL_BASE_URL}{separator}token={quote(raw_token)}"


def send_verification_email(to_email: str, raw_token: str) -> None:
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        logger.warning("Skipping verification email: Resend is not configured.")
        return

    resend.api_key = settings.RESEND_API_KEY
    verify_url = _verification_url(raw_token)
    html = (
        "<p>Welcome! Please verify your email to complete sign-up.</p>"
        f"<p><a href=\"{verify_url}\">Verify email</a></p>"
        "<p>If you did not request this, you can safely ignore this email.</p>"
    )

    try:
        resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": "Verify your email",
                "html": html,
            }
        )
    except Exception:
        logger.exception("Failed to send verification email.")
