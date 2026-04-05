"""Async query helpers — called exclusively from FastAPI route handlers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import OAuthAccount, Problem, Submission, User


# ---------------------------------------------------------------------------
# Problems
# ---------------------------------------------------------------------------

async def get_problem(db: AsyncSession, problem_id: uuid.UUID) -> Problem | None:
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    return result.scalar_one_or_none()


async def get_problem_with_sample_cases(db: AsyncSession, problem_id: uuid.UUID) -> Problem | None:
    """Return problem + only its sample test cases (is_sample=True).

    Hidden test cases are never exposed through the API.
    """
    result = await db.execute(
        select(Problem)
        .options(selectinload(Problem.test_cases))
        .where(Problem.id == problem_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

async def create_submission(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    problem_id: uuid.UUID,
    language: str,
    code: str,
) -> Submission:
    submission = Submission(
        id=job_id,
        user_id=user_id,
        problem_id=problem_id,
        language=language,
        code=code,
        status="pending",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


async def get_submission(db: AsyncSession, job_id: uuid.UUID) -> Submission | None:
    result = await db.execute(select(Submission).where(Submission.id == job_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    name: str | None,
    password_hash: str | None,
    is_verified: bool,
    verification_token_hash: str | None = None,
    verification_token_expires_at: datetime | None = None,
) -> User:
    user = User(
        email=email,
        name=name,
        password_hash=password_hash,
        is_verified=is_verified,
        verification_token_hash=verification_token_hash,
        verification_token_expires_at=verification_token_expires_at,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_verification_hash(db: AsyncSession, token_hash: str) -> User | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(User).where(
            User.verification_token_hash == token_hash,
            User.verification_token_expires_at.is_not(None),
            User.verification_token_expires_at >= now,
        )
    )
    return result.scalar_one_or_none()


async def mark_user_verified(db: AsyncSession, user: User) -> None:
    user.is_verified = True
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    await db.commit()


async def get_oauth_account(
    db: AsyncSession,
    *,
    provider: str,
    provider_account_id: str,
) -> OAuthAccount | None:
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_account_id == provider_account_id,
        )
    )
    return result.scalar_one_or_none()


async def get_oauth_account_by_user_provider(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
) -> OAuthAccount | None:
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def create_oauth_account(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
    provider_account_id: str,
) -> OAuthAccount:
    account = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_account_id=provider_account_id,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account
