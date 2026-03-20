"""POST /submit — validate, rate-limit, persist, and enqueue."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.base import get_db
from db.queries import create_submission, get_problem
from rate_limit import apply_rate_limits
from shared.models import SubmitRequest, SubmitResponse
from worker.tasks import evaluate_submission

router = APIRouter()


@router.post("/submit", response_model=SubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_code(
    body: SubmitRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmitResponse:
    """Accept a code submission.

    Validation order (fail-fast):
    1. JWT valid              — enforced by get_current_user dependency
    2. language in enum       — enforced by Pydantic model
    3. code <= 64 KB          — enforced by Pydantic model
    4. problem_id exists      — checked here against DB
    5. rate limit not exceeded — checked here via Redis
    """
    # 4. Problem must exist
    problem = await get_problem(db, body.problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

    # 5. Rate limiting (token bucket + sliding window)
    await apply_rate_limits(user_id)

    # Persist submission row (status=pending)
    job_id = uuid.uuid4()
    await create_submission(
        db,
        job_id=job_id,
        user_id=user_id,
        problem_id=body.problem_id,
        language=body.language.value,
        code=body.code,
    )

    # Enqueue Celery task (fire-and-forget)
    evaluate_submission.delay(str(job_id))

    return SubmitResponse(job_id=job_id)
