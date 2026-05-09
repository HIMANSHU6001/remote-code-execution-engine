"""GET /problems/{problem_id} — fetch problem details (sample cases only)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from auth.dependencies import get_current_user
from db.base import get_db
from db.models import Problem, Topic
from db.queries import create_problem, get_problem_with_sample_cases, get_problem_with_sample_cases_and_language_configs
from shared.enums import Difficulty
from shared.models import (
    LanguageConfigResponse,
    PaginatedProblemResponse,
    ProblemCreateRequest,
    ProblemListResponse,
    ProblemResponse,
    ProblemSampleTestCase,
    TopicResponse,
)

router = APIRouter()


@router.get("", response_model=PaginatedProblemResponse)
async def list_problems(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    difficulty: Difficulty | None = Query(None),
    topics: list[str] = Query(default=[]),
) -> PaginatedProblemResponse:
    """Get a paginated list of problems with optional filtering."""
    query = select(Problem)

    if difficulty:
        query = query.where(Problem.difficulty == difficulty)

    if topics:
        query = query.join(Problem.topics).where(Topic.slug.in_(topics)).distinct()

    # Count total items matching the filter
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Problem.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    query = query.options(selectinload(Problem.topics))

    result = await db.execute(query)
    problems = result.scalars().unique().all()

    return PaginatedProblemResponse(
        total=total,
        page=page,
        size=size,
        items=[ProblemListResponse.model_validate(p) for p in problems],
    )


@router.post("", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def post_problem(
    request: ProblemCreateRequest,
    user_id: Annotated[uuid.UUID, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProblemResponse:
    """Create a new problem with test cases."""
    # In a real app, you might verify the user's role here (e.g. admin or problem_setter)
    # Query topics if provided
    topics = []
    if request.topic_ids:
        result = await db.execute(select(Topic).where(Topic.id.in_(request.topic_ids)))
        topics = result.scalars().all()
        if len(topics) != len(set(request.topic_ids)):
            raise HTTPException(status_code=400, detail="One or more topic IDs are invalid.")

    problem = await create_problem(
        db,
        title=request.title,
        description=request.description,
        difficulty=request.difficulty,
        base_time_limit_ms=request.base_time_limit_ms,
        base_memory_limit_mb=request.base_memory_limit_mb,
        created_by=user_id,
        test_cases=[tc.model_dump() for tc in request.test_cases],
        topics=list(topics),
        hints=request.hints,
    )

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
        difficulty=problem.difficulty,
        base_time_limit_ms=problem.base_time_limit_ms,
        base_memory_limit_mb=problem.base_memory_limit_mb,
        hints=problem.hints,
        topics=[TopicResponse.model_validate(t) for t in problem.topics],
        sample_test_cases=sample_cases,
    )


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user)],  # noqa: ARG001 — auth enforced
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProblemResponse:
    """Return problem metadata, sample test cases, and language configs with boilerplate.

    Hidden test cases (is_sample=False) are NEVER returned.
    """
    problem = await get_problem_with_sample_cases_and_language_configs(db, problem_id)
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

    language_configs = [
        LanguageConfigResponse.model_validate(lc) for lc in problem.language_configs
    ]

    return ProblemResponse(
        id=problem.id,
        title=problem.title,
        difficulty=problem.difficulty,
        base_time_limit_ms=problem.base_time_limit_ms,
        base_memory_limit_mb=problem.base_memory_limit_mb,
        hints=problem.hints,
        topics=[TopicResponse.model_validate(t) for t in problem.topics],
        sample_test_cases=sample_cases,
        language_configs=language_configs,
    )
