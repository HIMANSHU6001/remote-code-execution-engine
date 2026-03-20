"""Async query helpers — called exclusively from FastAPI route handlers."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Problem, Submission


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
