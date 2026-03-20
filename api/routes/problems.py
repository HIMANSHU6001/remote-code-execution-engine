"""GET /problems/{problem_id} — fetch problem details (sample cases only)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.base import get_db
from db.queries import get_problem_with_sample_cases
from shared.models import ProblemResponse, ProblemSampleTestCase

router = APIRouter()


@router.get("/problems/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),  # noqa: ARG001 — auth enforced
    db: AsyncSession = Depends(get_db),
) -> ProblemResponse:
    """Return problem metadata and sample test cases.

    Hidden test cases (is_sample=False) are NEVER returned.
    """
    problem = await get_problem_with_sample_cases(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

    sample_cases = [
        ProblemSampleTestCase(
            id=tc.id,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            is_sample=tc.is_sample,
        )
        for tc in problem.test_cases
        if tc.is_sample
    ]

    return ProblemResponse(
        id=problem.id,
        title=problem.title,
        base_time_limit_ms=problem.base_time_limit_ms,
        base_memory_limit_mb=problem.base_memory_limit_mb,
        sample_test_cases=sample_cases,
    )
