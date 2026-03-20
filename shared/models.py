from __future__ import annotations

import uuid

from pydantic import UUID4, BaseModel, field_validator

from shared.enums import Language, SubmissionStatus, Verdict

# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------

class SubmitRequest(BaseModel):
    problem_id: UUID4
    language: Language
    code: str

    @field_validator("code")
    @classmethod
    def code_size(cls, v: str) -> str:
        if len(v.encode()) > 65_536:
            raise ValueError("code must be ≤ 64 KB")
        return v


# ---------------------------------------------------------------------------
# Outbound HTTP
# ---------------------------------------------------------------------------

class SubmitResponse(BaseModel):
    job_id: UUID4


class SubmissionDetailResponse(BaseModel):
    job_id: uuid.UUID
    status: SubmissionStatus
    verdict: Verdict | None = None
    execution_time_ms: int | None = None
    memory_used_mb: float | None = None
    stdout_snippet: str | None = None
    stderr_snippet: str | None = None


class ProblemSampleTestCase(BaseModel):
    id: uuid.UUID
    input_data: str
    expected_output: str
    is_sample: bool


class ProblemResponse(BaseModel):
    id: uuid.UUID
    title: str
    base_time_limit_ms: int
    base_memory_limit_mb: int
    sample_test_cases: list[ProblemSampleTestCase]


# ---------------------------------------------------------------------------
# WebSocket payloads
# ---------------------------------------------------------------------------

class WSAckPayload(BaseModel):
    type: str = "ack"
    job_id: str


class WSPingPayload(BaseModel):
    type: str = "ping"


class WSResultPayload(BaseModel):
    type: str = "result"
    job_id: str
    status: SubmissionStatus
    verdict: Verdict | None = None
    execution_time_ms: int | None = None
    memory_used_mb: float | None = None
    stdout_snippet: str | None = None
    stderr_snippet: str | None = None


class WSErrorPayload(BaseModel):
    type: str = "error"
    code: str  # NOT_FOUND | FORBIDDEN | UNAUTHORIZED
    detail: str


# ---------------------------------------------------------------------------
# Generic error response
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
