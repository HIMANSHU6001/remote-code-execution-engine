from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_s2s_claims
from auth.emailer import send_verification_email
from auth.security import create_access_token, hash_password, verify_password
from auth.verification import (
    generate_verification_token,
    hash_verification_token,
    verification_token_expiry,
)
from config.settings import settings
from db.base import get_db
from db.models import User
from db.queries import (
    create_oauth_account,
    create_user,
    get_oauth_account,
    get_oauth_account_by_user_provider,
    get_user_by_email,
    get_user_by_verification_hash,
    mark_user_verified,
)
from shared.models import (
    AuthTokenResponse,
    LoginRequest,
    SignupRequest,
    SignupResponse,
    SocialAuthRequest,
    SocialAuthResponse,
    VerifyEmailResponse,
)

router = APIRouter()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_social_claims(claims: dict[str, Any], body: SocialAuthRequest) -> None:
    claim_email = claims.get("email")
    if claim_email and _normalize_email(claim_email) != _normalize_email(body.email):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email mismatch in S2S token")

    claim_provider = claims.get("provider")
    if claim_provider and str(claim_provider).strip().lower() != body.provider:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Provider mismatch in S2S token")


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SignupResponse:
    normalized_email = _normalize_email(body.email)

    existing = await get_user_by_email(db, normalized_email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)

    user = await create_user(
        db,
        email=normalized_email,
        name=None,
        password_hash=hash_password(body.password),
        is_verified=False,
        verification_token_hash=token_hash,
        verification_token_expires_at=verification_token_expiry(),
    )

    # Intentionally non-blocking: endpoint returns 201 even if email delivery fails later.
    background_tasks.add_task(send_verification_email, normalized_email, raw_token)

    return SignupResponse(user_id=user.id, message="User created. Verification email queued.")


@router.get("/verify", response_model=VerifyEmailResponse)
async def verify_email(
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
) -> VerifyEmailResponse:
    token_hash = hash_verification_token(token)
    user = await get_user_by_verification_hash(db, token_hash)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    await mark_user_verified(db, user)
    return VerifyEmailResponse(message="Email verified successfully")


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthTokenResponse:
    normalized_email = _normalize_email(body.email)
    user = await get_user_by_email(db, normalized_email)

    if user is None or user.password_hash is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return AuthTokenResponse(access_token=token, expires_in=settings.JWT_ACCESS_TTL_SECONDS)


@router.post("/social", response_model=SocialAuthResponse)
async def social_auth(
    body: SocialAuthRequest,
    claims: dict[str, Any] = Depends(get_s2s_claims),
    db: AsyncSession = Depends(get_db),
) -> SocialAuthResponse:
    _validate_social_claims(claims, body)

    normalized_email = _normalize_email(body.email)

    oauth_account = await get_oauth_account(
        db,
        provider=body.provider,
        provider_account_id=body.provider_account_id,
    )

    if oauth_account is not None:
        user = await db.get(User, oauth_account.user_id)
    else:
        user = await get_user_by_email(db, normalized_email)
        if user is None:
            user = await create_user(
                db,
                email=normalized_email,
                name=body.name.strip() if body.name else None,
                password_hash=None,
                is_verified=True,
            )

        existing_provider_for_user = await get_oauth_account_by_user_provider(
            db,
            user_id=user.id,
            provider=body.provider,
        )
        if (
            existing_provider_for_user is not None
            and existing_provider_for_user.provider_account_id != body.provider_account_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider already linked to a different account id",
            )

        if existing_provider_for_user is None:
            await create_oauth_account(
                db,
                user_id=user.id,
                provider=body.provider,
                provider_account_id=body.provider_account_id,
            )

        user_changed = False
        if not user.is_verified:
            user.is_verified = True
            user_changed = True
        if body.name and not user.name:
            user.name = body.name.strip()
            user_changed = True

        if user_changed:
            await db.commit()
            await db.refresh(user)

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to resolve user")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return SocialAuthResponse(
        access_token=token,
        expires_in=settings.JWT_ACCESS_TTL_SECONDS,
        user_id=user.id,
    )
