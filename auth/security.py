from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext  # type: ignore[reportMissingModuleSource]

from config.settings import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(*, user_id: uuid.UUID, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.JWT_ACCESS_TTL_SECONDS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_s2s_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.S2S_JWT_SECRET,
        algorithms=[settings.S2S_JWT_ALGORITHM],
        audience=settings.S2S_JWT_AUDIENCE,
        issuer=settings.S2S_JWT_ISSUER,
        options={"require": ["iss", "aud", "iat", "exp", "jti"]},
    )
    return payload
