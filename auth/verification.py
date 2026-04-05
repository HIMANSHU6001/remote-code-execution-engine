from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from config.settings import settings


def generate_verification_token() -> str:
    # token_urlsafe(32) uses 32 random bytes and is URL-safe for query params.
    return secrets.token_urlsafe(32)


def hash_verification_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def verification_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=settings.VERIFICATION_TOKEN_TTL_SECONDS)
