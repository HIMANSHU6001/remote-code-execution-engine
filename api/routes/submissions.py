"""GET /submissions/{job_id} — poll submission status."""

from __future__ import annotations

import uuid
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.base import get_db, get_redis
from db.queries import get_submission
from shared.models import SubmissionDetailResponse

router = APIRouter()

@router.get("/submissions/{job_id}", response_model=SubmissionDetailResponse)
async def get_submission_status(
    job_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Any, Depends(get_redis)], # Inject Redis
) -> SubmissionDetailResponse:
    
    submission = await get_submission(db, job_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    if submission.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Start building the base response
    response_data = {
        "job_id": submission.id,
        "status": submission.status,
        "verdict": submission.verdict,
        "execution_time_ms": submission.execution_time_ms,
        "memory_used_mb": float(submission.memory_used_mb) if submission.memory_used_mb is not None else None,
        "stdout_snippet": submission.stdout_snippet,
        "stderr_snippet": submission.stderr_snippet,
        "actual_output": submission.actual_output,
        "expected_output": submission.expected_output,
        "passed_test_cases": submission.passed_test_cases,
        "total_test_cases": submission.total_test_cases,
        "failed_test_case_id": submission.failed_test_case_id,
        "details": None
    }
    
    if not submission.is_submit and submission.status == "completed":
        # Force job_id to string to ensure the key is formatted correctly
        redis_key = f"run_details:{str(job_id)}"
        cached_details = await redis.get(redis_key)
        
        print(f"Checking Redis for run details with key: {redis_key} | Found: {cached_details is not None}")
        
        if cached_details:
            response_data["details"] = json.loads(cached_details)

    return SubmissionDetailResponse(**response_data)