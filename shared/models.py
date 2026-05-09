from __future__ import annotations

import uuid

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field, field_validator

from shared.enums import Difficulty, Language, SubmissionStatus, SupportedLanguage, Verdict

# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------


class SubmitRequest(BaseModel):
    problem_id: UUID4
    language: Language
    code: str
    is_submit: bool = True

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
    actual_output: str | None = None
    expected_output: str | None = None
    passed_test_cases: int = 0
    total_test_cases: int = 0
    details: list[dict] | None = None
    failed_test_case_id: uuid.UUID | None = None


class ProblemSampleTestCase(BaseModel):
    id: uuid.UUID
    input_data: str
    expected_output: str
    is_sample: bool


class LanguageConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: SupportedLanguage
    boilerplate: str
    driver_code: str


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class ProblemListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    difficulty: Difficulty
    topics: list[TopicResponse] = []


class PaginatedProblemResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ProblemListResponse]


class ProblemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    difficulty: Difficulty
    base_time_limit_ms: int
    base_memory_limit_mb: int
    hints: list[str] = []
    topics: list[TopicResponse] = []
    sample_test_cases: list[ProblemSampleTestCase]
    language_configs: list[LanguageConfigResponse] = []


class TestCaseCreateRequest(BaseModel):
    input_data: str
    expected_output: str
    is_sample: bool = False
    ordering: int = 0


class ProblemCreateRequest(BaseModel):
    title: str
    description: str
    difficulty: Difficulty
    base_time_limit_ms: int
    base_memory_limit_mb: int
    hints: list[str] = Field(default=[], max_length=4)
    topic_ids: list[int] = Field(default=[])
    test_cases: list[TestCaseCreateRequest]


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
    actual_output: str | None = None
    expected_output: str | None = None


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


# ---------------------------------------------------------------------------
# Auth inbound
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SocialAuthRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    provider: str
    provider_account_id: str

    @field_validator("provider")
    @classmethod
    def provider_non_empty(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("provider must be non-empty")
        return cleaned

    @field_validator("provider_account_id")
    @classmethod
    def provider_account_id_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("provider_account_id must be non-empty")
        return cleaned


# ---------------------------------------------------------------------------
# Auth outbound
# ---------------------------------------------------------------------------


class SignupResponse(BaseModel):
    user_id: uuid.UUID
    message: str


class VerifyEmailResponse(BaseModel):
    message: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SocialAuthResponse(AuthTokenResponse):
    user_id: uuid.UUID
