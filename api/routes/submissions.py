"""GET /submissions/{job_id} — poll submission status."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.base import get_db
from db.queries import get_submission
from shared.models import SubmissionDetailResponse

router = APIRouter()


@router.get("/submissions/{job_id}", response_model=SubmissionDetailResponse)
async def get_submission_status(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionDetailResponse:
    """Return current status of a submission.

    Users may only query their own submissions (403 if ownership mismatch).
    Returns 200 with status='running' and null verdict fields while in progress.
    """
    submission = await get_submission(db, job_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    if submission.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return SubmissionDetailResponse(
        job_id=submission.id,
        status=submission.status,
        verdict=submission.verdict,
        execution_time_ms=submission.execution_time_ms,
        memory_used_mb=float(submission.memory_used_mb) if submission.memory_used_mb is not None else None,
        stdout_snippet=submission.stdout_snippet,
        stderr_snippet=submission.stderr_snippet,
    )
