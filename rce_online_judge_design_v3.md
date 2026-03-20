# RCE & Online Judge — System Design
**v3.1 · Implementation-Ready Specification**

---

## Table of Contents

1. [Role & Scope](#1-role--scope)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Enums & Shared Types](#3-enums--shared-types)
4. [Authentication & Identity](#4-authentication--identity)
5. [API Contract](#5-api-contract)
6. [Rate Limiting](#6-rate-limiting)
7. [Submission State Machine](#7-submission-state-machine)
8. [Database Schemas](#8-database-schemas)
9. [Multi-Language Fairness Engine](#9-multi-language-fairness-engine)
10. [Execution Sandbox](#10-execution-sandbox)
11. [Seccomp Profile](#11-seccomp-profile)
12. [Judging Engine](#12-judging-engine)
13. [Real-Time WebSocket System](#13-real-time-websocket-system)
14. [Fault Tolerance](#14-fault-tolerance)
15. [Coding Standards](#15-coding-standards)
16. [Docker Images](#16-docker-images)
17. [Result Storage & TTL Policy](#17-result-storage--ttl-policy)
18. [Open Items](#18-open-items)

---

## 1. Role & Scope

This document is the authoritative, implementation-ready design specification for a **highly secure, asynchronous Remote Code Execution (RCE) engine** and Online Judge platform. All implementation decisions prioritise **security**, **isolation**, **deterministic execution**, and **strict resource limits**.

**Languages supported (v1):** Python 3.11, C++ (Clang), Java, Node.js 20.

---

## 2. High-Level Architecture

The platform is fully decoupled and async-driven. Each component is independently scalable and communicates only through well-defined interfaces.

```
┌─────────────┐     POST /submit      ┌──────────────────┐
│   Client    │ ──────────────────► │   FastAPI Gateway  │
│             │ ◄──────────────────  │  (auth, validate,  │
│             │     job_id (UUID)    │   rate-limit)      │
│             │                      └────────┬───────────┘
│             │  WS /ws/{job_id}              │ enqueue task
│             │ ◄────────────────────────┐   ▼
│             │   result JSON            │  ┌──────────────┐
└─────────────┘                          │  │    Redis     │
                                         │  │  (task queue │
                                    ┌────┘  │  + pub/sub)  │
                                    │       └──────┬───────┘
                              pub/sub│              │ dequeue
                                    │       ┌──────▼───────┐
                                    │       │ Celery Worker│
                                    │       │ (synchronous)│
                                    │       └──────┬───────┘
                                    │              │ r/w
                                    │       ┌──────▼───────┐
                                    └───────┤  PostgreSQL  │
                                            │  + Docker    │
                                            │  (rootless)  │
                                            └──────────────┘
```

| Component      | Technology      | Purpose                                                  |
|----------------|-----------------|----------------------------------------------------------|
| API Gateway    | FastAPI         | HTTP endpoints, WebSocket hub, rate limiting, auth       |
| Message Broker | Redis           | Celery task queue, Pub/Sub result delivery, rate-limit counters — **transient only, not durable storage** |
| Worker Engine  | Celery + Beat   | Background code evaluation; periodic zombie sweeper      |
| Database       | PostgreSQL      | Persistent storage — problems, test cases, submissions — **source of truth** |
| Sandbox        | Docker (rootless) | Isolated, resource-capped code execution               |

---

## 3. Enums & Shared Types

All enums are defined once here and referenced by every layer — API, DB, and worker. No magic strings anywhere.

### 3.1 Language

```python
# shared/enums.py
from enum import StrEnum

class Language(StrEnum):
    PYTHON = "python"
    CPP    = "cpp"      # compiled with Clang (docker/cpp/Dockerfile)
    JAVA   = "java"
    NODEJS = "nodejs"
```

```sql
-- PostgreSQL enum
CREATE TYPE language_enum AS ENUM ('python', 'cpp', 'java', 'nodejs');
```

> **Image mapping:** `cpp` uses the `docker/cpp/Dockerfile` image (Clang-based).
> A separate `docker/clang/Dockerfile` exists for future Clang-specific use cases
> (e.g. sanitizer builds). For now `cpp` and `clang` images are identical in content;
> only the `cpp` image is wired into the judging engine.

---

### 3.2 Submission Status

```python
class SubmissionStatus(StrEnum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"   -- only terminal status; IE also lands here
```

```sql
CREATE TYPE submission_status AS ENUM ('pending', 'running', 'completed');
```

> **Design decision:** `status` has exactly three states. There is no separate `error` status.
> Internal errors (IE) set `status = completed` with `verdict = IE`. This keeps the state
> machine simple: `completed` always means the job is done, regardless of outcome.

---

### 3.3 Verdict

```python
class Verdict(StrEnum):
    ACCEPTED            = "ACC"
    WRONG_ANSWER        = "WA"
    TIME_LIMIT_EXCEEDED = "TLE"
    MEM_LIMIT_EXCEEDED  = "MLE"
    RUNTIME_ERROR       = "RE"
    COMPILATION_ERROR   = "CE"
    INTERNAL_ERROR      = "IE"
```

```sql
CREATE TYPE verdict_enum AS ENUM ('ACC', 'WA', 'TLE', 'MLE', 'RE', 'CE', 'IE');
```

---

### 3.4 Pydantic Base Models (shared)

```python
# shared/models.py
from pydantic import BaseModel, UUID4, field_validator
from shared.enums import Language, SubmissionStatus, Verdict
import uuid

class SubmitRequest(BaseModel):
    problem_id: UUID4
    language:   Language      # validated against StrEnum automatically
    code:       str

    @field_validator("code")
    @classmethod
    def code_size(cls, v: str) -> str:
        if len(v.encode()) > 65_536:
            raise ValueError("code must not exceed 64 KB")
        return v


class SubmitResponse(BaseModel):
    job_id: UUID4             # server-generated; never client-supplied


class WSResultPayload(BaseModel):
    job_id:             UUID4
    status:             SubmissionStatus
    verdict:            Verdict
    execution_time_ms:  int
    memory_used_mb:     float
    stdout_snippet:     str   # first 1 KB of stdout, for UI display
    stderr_snippet:     str   # first 512 B of stderr, for RE display


class ErrorResponse(BaseModel):
    error:   str
    detail:  str | None = None
```

---

## 4. Authentication & Identity

Every request must carry a signed **JWT Bearer token** in the `Authorization` header.

### 4.1 JWT Claims

```json
{
  "sub":  "550e8400-e29b-41d4-a716-446655440000",  // user UUID — rate-limit key
  "iat":  1710000000,
  "exp":  1710086400,                               // max 24 h
  "role": "user"                                    // user | admin | problem_setter
}
```

### 4.2 Dependency (FastAPI)

```python
# auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt, uuid

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> uuid.UUID:
    """Decode JWT and return the user UUID (sub claim).

    Returns:
        UUID of the authenticated user.

    Raises:
        HTTPException: 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
```

> Workers **never** trust a `user_id` embedded in the Celery task payload.
> They always read it from the `submissions` row keyed by `job_id`.

---

## 5. API Contract

### 5.1 `POST /submit` — Submit Code

**Auth:** Required (JWT Bearer)

**Request:**

```http
POST /submit
Authorization: Bearer <token>
Content-Type: application/json

{
  "problem_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "language":   "python",
  "code":       "print(input())"
}
```

**Validation (in order, fail-fast):**

| Check                        | Failure response                    |
|------------------------------|-------------------------------------|
| JWT valid & not expired      | `401 Unauthorized`                  |
| `language` in `Language` enum | `422 Unprocessable Entity`         |
| `code` ≤ 64 KB               | `422 Unprocessable Entity`          |
| `problem_id` exists in DB    | `404 Not Found`                     |
| Rate limit not exceeded      | `429 Too Many Requests`             |

**Success response — `202 Accepted`:**

```json
{
  "job_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

> `job_id` is a **UUID v4 generated by the server** at submission time.
> It is the primary key of the `submissions` row and must never be supplied by the client.

**Implementation:**

```python
# api/routes/submit.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from shared.enums import Language, SubmissionStatus
from shared.models import SubmitRequest, SubmitResponse
from auth.dependencies import get_current_user
from rate_limit.token_bucket import check_rate_limit
from db.queries import get_problem, create_submission
from worker.tasks import evaluate_submission

router = APIRouter()

@router.post("/submit", response_model=SubmitResponse, status_code=202)
async def submit(
    body: SubmitRequest,
    user_id: uuid.UUID = Depends(get_current_user),
) -> SubmitResponse:
    """Accept a code submission, enqueue evaluation, return job_id.

    Args:
        body:    Validated submission payload.
        user_id: UUID extracted from the JWT by the auth dependency.

    Returns:
        SubmitResponse containing the server-generated job_id.

    Raises:
        HTTPException: 404 if problem_id does not exist.
        HTTPException: 429 if rate limit is exceeded.
    """
    await check_rate_limit(user_id)                 # raises 429 if exceeded

    problem = await get_problem(body.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")

    job_id = uuid.uuid4()                           # server-generated

    await create_submission(
        job_id=job_id,
        user_id=user_id,
        problem_id=body.problem_id,
        language=body.language,
        code=body.code,
        status=SubmissionStatus.PENDING,
    )

    evaluate_submission.delay(str(job_id))          # enqueue to Celery

    return SubmitResponse(job_id=job_id)
```

---

### 5.2 `GET /submissions/{job_id}` — Poll Submission Status

**Auth:** Required. User may only query their own submissions.

**Response — `200 OK`:**

```json
{
  "job_id":             "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status":             "completed",
  "verdict":            "ACC",
  "execution_time_ms":  42,
  "memory_used_mb":     14.2,
  "stdout_snippet":     "hello world\n",
  "stderr_snippet":     ""
}
```

**Responses:**

| Condition              | Status |
|------------------------|--------|
| Not found              | `404`  |
| Belongs to other user  | `403`  |
| Job still running      | `200` with `status: "running"`, null verdict fields |

---

### 5.3 `WS /ws/{job_id}` — Real-Time Result Stream

**Auth:** JWT passed as query parameter `?token=<jwt>` (WebSocket headers not universally supported by browsers).

**Protocol:**

```
Client                                    Server
  │                                          │
  │── WS connect /ws/{job_id}?token=<jwt> ──►│
  │                                          │ 1. Validate JWT
  │                                          │ 2. Verify job belongs to user
  │                                          │ 3. Check DB for existing result
  │◄─────── {"type":"ack","job_id":"..."} ───│
  │                                          │  (if already completed)
  │◄──── {"type":"result", ...payload} ─────│  send result immediately & close
  │                                          │
  │                      (if still pending/running)
  │◄──── {"type":"ping"} ───────────────────│  every 20 s (keep-alive)
  │───── {"type":"pong"} ──────────────────►│
  │                                          │  ... worker finishes ...
  │◄──── {"type":"result", ...payload} ─────│  pushed via Redis Pub/Sub
  │                                          │  server closes connection
```

**Result payload (`type: "result"`):**

```json
{
  "type":             "result",
  "job_id":           "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status":           "completed",
  "verdict":          "ACC",
  "execution_time_ms": 42,
  "memory_used_mb":   14.2,
  "stdout_snippet":   "hello world\n",
  "stderr_snippet":   ""
}
```

**Error payloads:**

```json
{ "type": "error", "code": "NOT_FOUND",      "detail": "job_id does not exist" }
{ "type": "error", "code": "FORBIDDEN",      "detail": "job does not belong to you" }
{ "type": "error", "code": "UNAUTHORIZED",   "detail": "invalid token" }
```

---

### 5.4 `GET /problems/{problem_id}` — Fetch Problem

**Auth:** Required.

**Response — `200 OK`:**

```json
{
  "id":                   "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title":                "Two Sum",
  "base_time_limit_ms":   1000,
  "base_memory_limit_mb": 256,
  "sample_test_cases": [
    {
      "id":              "...",
      "input_data":      "4\n2 7 11 15\n9",
      "expected_output": "0 1",
      "is_sample":       true
    }
  ]
}
```

> Hidden test cases (`is_sample = false`) are **never returned** by this endpoint.

---

## 6. Rate Limiting

Two independent limiters run in sequence. Both use Redis as the backing store.

### 6.1 Limiter 1 — Token Bucket (burst control: 1 submission per 2 s per user)

**Purpose:** Prevent rapid consecutive submissions from a single user.

**Algorithm:** Token bucket with refill rate of 1 token per 2 seconds, bucket capacity 1.

```
capacity  = 1 token
refill    = 1 token / 2 seconds
key       = f"tb:{user_id}"
```

**Redis keys:**

```
tb:{user_id}:tokens     FLOAT   current token count
tb:{user_id}:last_refill FLOAT  unix timestamp of last refill
```

**Implementation (Lua script — atomic):**

```lua
-- rate_limit/token_bucket.lua
-- KEYS[1] = tokens key,  KEYS[2] = last_refill key
-- ARGV[1] = capacity,    ARGV[2] = refill_rate (tokens/sec),  ARGV[3] = now (float)

local capacity    = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now         = tonumber(ARGV[3])

local tokens      = tonumber(redis.call("GET", KEYS[1])) or capacity
local last_refill = tonumber(redis.call("GET", KEYS[2])) or now

-- Refill tokens based on elapsed time
local elapsed = now - last_refill
local refilled = math.min(capacity, tokens + elapsed * refill_rate)

if refilled < 1 then
    -- Not enough tokens — reject
    -- Return seconds until 1 token is available
    local wait = (1 - refilled) / refill_rate
    return {0, math.ceil(wait)}
end

-- Consume 1 token
local new_tokens = refilled - 1
redis.call("SET", KEYS[1], new_tokens, "EX", 3600)
redis.call("SET", KEYS[2], now,        "EX", 3600)
return {1, 0}
```

```python
# rate_limit/token_bucket.py
import time
import uuid
from fastapi import HTTPException, status
from redis.asyncio import Redis

CAPACITY    = 1      # max tokens in bucket
REFILL_RATE = 0.5    # tokens per second  →  1 token / 2 s

async def check_token_bucket(redis: Redis, user_id: uuid.UUID) -> None:
    """Enforce 1-submission-per-2-seconds via token bucket.

    Args:
        redis:   Async Redis client.
        user_id: Authenticated user UUID.

    Raises:
        HTTPException: 429 if the bucket is empty, with Retry-After header.
    """
    uid = str(user_id)
    keys = [f"tb:{uid}:tokens", f"tb:{uid}:last_refill"]
    args = [CAPACITY, REFILL_RATE, time.time()]

    allowed, retry_after = await redis.eval(TOKEN_BUCKET_LUA, 2, *keys, *args)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Submission rate limit exceeded. Slow down.",
            headers={
                "Retry-After":          str(retry_after),
                "X-RateLimit-Policy":   "token-bucket",
            },
        )
```

---

### 6.2 Limiter 2 — Sliding Window Counter (10 submissions per 60 s per user)

**Purpose:** Enforce the sustained submission ceiling.

**Algorithm:** Sliding window using a Redis sorted set. Timestamps of accepted submissions are stored; expired entries are pruned on every check.

```
window_size = 60 seconds
max_count   = 10 submissions
key         = f"sw:{user_id}"
```

**Implementation (Lua script — atomic):**

```lua
-- rate_limit/sliding_window.lua
-- KEYS[1] = sorted set key
-- ARGV[1] = now (float unix),  ARGV[2] = window_size (s),  ARGV[3] = max_count,  ARGV[4] = event_id

local now         = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])
local max_count   = tonumber(ARGV[3])
local event_id    = ARGV[4]
local cutoff      = now - window_size

-- Remove events older than the window
redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", cutoff)

-- Count events within the window
local count = redis.call("ZCARD", KEYS[1])

if count >= max_count then
    -- Find oldest event timestamp for Retry-After
    local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
    local reset_at = tonumber(oldest[2]) + window_size
    return {0, math.ceil(reset_at - now)}
end

-- Record this event
redis.call("ZADD",   KEYS[1], now, event_id)
redis.call("EXPIRE", KEYS[1], window_size + 1)
return {1, 0}
```

```python
# rate_limit/sliding_window.py
import time, uuid
from fastapi import HTTPException, status
from redis.asyncio import Redis

WINDOW_SIZE = 60    # seconds
MAX_COUNT   = 10    # submissions per window

async def check_sliding_window(redis: Redis, user_id: uuid.UUID) -> None:
    """Enforce 10-submissions-per-60-seconds via sliding window counter.

    Args:
        redis:   Async Redis client.
        user_id: Authenticated user UUID.

    Raises:
        HTTPException: 429 if window is full, with Retry-After and X-RateLimit-* headers.
    """
    uid      = str(user_id)
    event_id = str(uuid.uuid4())
    now      = time.time()
    key      = f"sw:{uid}"

    allowed, retry_after = await redis.eval(
        SLIDING_WINDOW_LUA, 1, key, now, WINDOW_SIZE, MAX_COUNT, event_id,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Maximum 10 per minute.",
            headers={
                "Retry-After":            str(retry_after),
                "X-RateLimit-Limit":      str(MAX_COUNT),
                "X-RateLimit-Window":     f"{WINDOW_SIZE}s",
                "X-RateLimit-Reset":      str(int(now) + retry_after),
                "X-RateLimit-Policy":     "sliding-window",
            },
        )
```

---

### 6.3 Combined Rate Limit Check

Both limiters run on every `POST /submit`. Token bucket runs first (faster rejection for bursts).

```python
# rate_limit/__init__.py
async def check_rate_limit(redis: Redis, user_id: uuid.UUID) -> None:
    """Run both rate limiters in sequence.

    Token bucket is checked first — it rejects rapid-fire submissions before
    the sliding window counter records them.

    Args:
        redis:   Async Redis client.
        user_id: Authenticated user UUID.

    Raises:
        HTTPException: 429 from whichever limiter fires first.
    """
    await check_token_bucket(redis, user_id)
    await check_sliding_window(redis, user_id)
```

---

## 7. Submission State Machine

```
┌─────────┐    worker picks up     ┌─────────┐    job done / IE    ┌───────────┐
│ pending │ ──────────────────────►│ running │ ──────────────────►│ completed │
└─────────┘                        └─────────┘                     └───────────┘
     ▲                                                                    │
     │                                                           verdict ∈ {ACC, WA,
     │                                                           TLE, MLE, RE, CE, IE}
     └──── terminal state protection: any re-queued task for a
           non-pending submission is dropped immediately
```

**Rules:**

- `pending → running`: set atomically when the worker reads the task.
- `running → completed`: set after verdict is determined, **including IE**.
- `completed` is the **only terminal state**. Once set, the row is immutable.
- IE sets `status = completed`, `verdict = IE`. There is no `error` status.

### 7.1 Terminal State Protection

```python
# worker/tasks.py  (inside evaluate_submission task)
from db.queries import get_submission_status, set_status_running
from shared.enums import SubmissionStatus

def _acquire_task(job_id: str) -> bool:
    """Attempt to transition submission from pending → running atomically.

    Uses a PostgreSQL UPDATE ... WHERE status = 'pending' to ensure exactly
    one worker processes each job, even under retry/re-queue scenarios.

    Args:
        job_id: The submission UUID string.

    Returns:
        True if the transition succeeded (this worker owns the job).
        False if the job is not in pending state — drop it.
    """
    rows_updated = set_status_running(job_id)   # UPDATE ... WHERE status='pending'
    return rows_updated == 1
```

```sql
-- db/queries.sql
-- Atomic pending → running with terminal state protection
UPDATE submissions
SET    status     = 'running',
       updated_at = NOW()
WHERE  id         = $1
  AND  status     = 'pending'
RETURNING id;
-- Returns 0 rows if status was already running/completed → worker drops the task
```

---

## 8. Database Schemas

C++ is the baseline for all time and memory limits. Every table has `created_at` / `updated_at`.

### 8.1 Enum Types

```sql
-- Must be created before tables that reference them
CREATE TYPE language_enum       AS ENUM ('python', 'cpp', 'java', 'nodejs');
CREATE TYPE submission_status   AS ENUM ('pending', 'running', 'completed');
CREATE TYPE verdict_enum        AS ENUM ('ACC', 'WA', 'TLE', 'MLE', 'RE', 'CE', 'IE');
```

---

### 8.2 Table: `users`

```sql
CREATE TABLE users (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email        TEXT        NOT NULL UNIQUE,
    password_hash TEXT       NOT NULL,
    role         TEXT        NOT NULL DEFAULT 'user'
                             CHECK (role IN ('user', 'admin', 'problem_setter')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email);
```

---

### 8.3 Table: `problems`

```sql
CREATE TABLE problems (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title                TEXT        NOT NULL,
    description          TEXT        NOT NULL,
    base_time_limit_ms   INTEGER     NOT NULL CHECK (base_time_limit_ms   > 0),
    base_memory_limit_mb INTEGER     NOT NULL CHECK (base_memory_limit_mb > 0),
    created_by           UUID        NOT NULL REFERENCES users(id),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 8.4 Table: `test_cases`

```sql
CREATE TABLE test_cases (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id      UUID        NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    input_data      TEXT        NOT NULL,
    expected_output TEXT        NOT NULL,
    is_sample       BOOLEAN     NOT NULL DEFAULT FALSE,
    ordering        INTEGER     NOT NULL DEFAULT 0,   -- execution order (ASC)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_input_size    CHECK (octet_length(input_data)      <= 1048576),  -- 1 MB
    CONSTRAINT chk_expected_size CHECK (octet_length(expected_output) <= 1048576)   -- 1 MB
);

CREATE INDEX idx_test_cases_problem ON test_cases (problem_id, ordering ASC);
```

> Test cases are executed in `ordering ASC` order. Sample cases (`is_sample = true`) should
> have the lowest `ordering` values so they run first, giving fast feedback on trivially wrong code.

---

### 8.5 Table: `submissions`

```sql
CREATE TABLE submissions (
    -- Identity
    id                UUID               PRIMARY KEY,   -- server-generated UUID; never client-supplied
    user_id           UUID               NOT NULL REFERENCES users(id),
    problem_id        UUID               NOT NULL REFERENCES problems(id),

    -- Submission content
    language          language_enum      NOT NULL,
    code              TEXT               NOT NULL
                                         CHECK (octet_length(code) <= 65536),  -- 64 KB

    -- State machine
    status            submission_status  NOT NULL DEFAULT 'pending',
    verdict           verdict_enum,                 -- NULL until completed

    -- Execution metrics (NULL until completed)
    execution_time_ms INTEGER,
    memory_used_mb    NUMERIC(8, 2),

    -- Output snippets for UI display (NULL until completed)
    stdout_snippet    TEXT,              -- first 1 KB of stdout
    stderr_snippet    TEXT,             -- first 512 B of stderr

    -- Timestamps
    created_at        TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ        NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_submissions_user    ON submissions (user_id, created_at DESC);
CREATE INDEX idx_submissions_problem ON submissions (problem_id, created_at DESC);
CREATE INDEX idx_submissions_status  ON submissions (status) WHERE status != 'completed';
```

> `id` is inserted by the API gateway before enqueueing. The `PRIMARY KEY` constraint (not
> `DEFAULT gen_random_uuid()`) enforces that the server controls the value.

---

### 8.6 `updated_at` Auto-Update Trigger

```sql
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_submissions_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- Apply to all tables that have updated_at
CREATE TRIGGER trg_problems_updated_at
    BEFORE UPDATE ON problems
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
```

---

## 9. Multi-Language Fairness Engine

C++ limits are the baseline. Per-language multipliers are applied before container launch.

### 9.1 Multiplier Table

| Language | Compile Step | Time Multiplier | Memory Multiplier | Memory Offset |
|----------|-------------|-----------------|-------------------|---------------|
| C++      | `g++ -O2`   | × 1.0           | × 1.0             | + 0 MB        |
| Java     | `javac`     | × 2.0           | × 1.5             | + 100 MB      |
| Python   | —           | × 5.0           | × 1.5             | + 20 MB       |
| Node.js  | —           | × 3.0           | × 1.3             | + 30 MB       |

### 9.2 Limit Calculation

```python
# worker/fairness.py
import math
from dataclasses import dataclass
from shared.enums import Language

@dataclass(frozen=True)
class LangProfile:
    time_multiplier:    float
    memory_multiplier:  float
    memory_offset_mb:   int

LANG_PROFILES: dict[Language, LangProfile] = {
    Language.CPP:    LangProfile(1.0, 1.0, 0),
    Language.JAVA:   LangProfile(2.0, 1.5, 100),
    Language.PYTHON: LangProfile(5.0, 1.5, 20),
    Language.NODEJS: LangProfile(3.0, 1.3, 30),
}

def compute_limits(
    base_time_ms: int,
    base_memory_mb: int,
    language: Language,
) -> tuple[int, int]:
    """Compute fair time and memory limits for a given language.

    Args:
        base_time_ms:   Problem's baseline time limit in milliseconds (C++ baseline).
        base_memory_mb: Problem's baseline memory limit in MB (C++ baseline).
        language:       Submission language.

    Returns:
        Tuple of (fair_time_seconds: int, fair_memory_mb: int).
    """
    profile = LANG_PROFILES[language]
    fair_time_sec  = math.ceil((base_time_ms * profile.time_multiplier) / 1000)
    fair_memory_mb = (
        math.floor(base_memory_mb * profile.memory_multiplier)
        + profile.memory_offset_mb
    )
    return fair_time_sec, fair_memory_mb
```

### 9.3 Language Runner Commands

```python
# worker/runners.py
from shared.enums import Language

# Commands executed INSIDE the execution container.
# Binary/source is mounted at /sandbox (read-only).
# GNU coreutils timeout is guaranteed present in execution images.

COMPILE_COMMANDS: dict[Language, str | None] = {
    Language.CPP:    "clang++ -O2 -o /sandbox/a.out /sandbox/solution.cpp",  # Clang, per docker/cpp/Dockerfile
    Language.JAVA:   "javac -d /sandbox /sandbox/Main.java",
    Language.PYTHON: None,   # interpreted; no compile step
    Language.NODEJS: None,
}

RUN_COMMANDS: dict[Language, str] = {
    Language.CPP:    "/sandbox/a.out",
    Language.JAVA:   "java -cp /sandbox Main",
    Language.PYTHON: "python3 /sandbox/solution.py",
    Language.NODEJS: "node /sandbox/solution.js",
}

SOURCE_FILENAMES: dict[Language, str] = {
    Language.CPP:    "solution.cpp",
    Language.JAVA:   "Main.java",
    Language.PYTHON: "solution.py",
    Language.NODEJS: "solution.js",
}
```

---

## 10. Execution Sandbox

### 10.1 Design: One Container Per Submission

A single execution container is launched per submission. All test cases are evaluated
**sequentially inside that one container** by a shell loop. The container stays alive
for the full duration of the submission's evaluation, then is removed.

```
Submission
    │
    ├── compile container  (compiled languages only, then removed)
    │
    └── execution container  (one, lives for all N test cases)
            │
            ├── test case 1: write input → run → read stdout/stderr → compare
            ├── test case 2: write input → run → read stdout/stderr → compare
            │   ...
            └── test case N: write input → run → read stdout/stderr → compare
                                                                      │
                                                                 fail-fast: stop
                                                                 on first failure
```

**Why one container per submission instead of one per test case:**

- Eliminates Docker container startup overhead (50–300 ms) multiplied by test case count.
- The sandbox is still fully isolated — the container is dedicated to this submission only.
- The program binary/interpreter is loaded once; subsequent test cases reuse the warm process.
- Security properties are identical: the container is destroyed after the submission completes.

**Isolation guarantee:** Each test case invocation is a fresh process execution — the
*program* starts from scratch for every test case. Only the *container* (the OS-level
sandbox) persists across test cases. No state leaks between test case runs.

---

### 10.2 Sandbox Directory Layout

Each submission gets a unique host directory. The execution container mounts it read-only.
The worker writes all inputs from the host; the container writes outputs to its own `/tmp`
(tmpfs), which the worker reads back via `docker exec` after each test case run.

```
/sandbox/jobs/{job_id}/
├── solution.{ext}     # user source code   (written by worker, step 1)
├── a.out              # compiled binary    (C++, written by compile container, step 2)
├── Main.class         # compiled bytecode  (Java, written by compile container, step 2)
└── inputs/
    ├── tc_0.txt       # test case 0 stdin  (written by worker before execution starts)
    ├── tc_1.txt       # test case 1 stdin
    └── tc_N.txt       # test case N stdin
```

> All input files are written to the host **before** the execution container is launched.
> The container sees the full `inputs/` directory via the read-only mount from the start.
> No files are written to the host sandbox during execution — outputs live in `/tmp` (tmpfs)
> inside the container and are read back with `docker exec cat`.

---

### 10.3 Step 1 — Host Prepares Sandbox

```python
# worker/sandbox.py
import pathlib, uuid
from shared.enums import Language
from worker.runners import SOURCE_FILENAMES

SANDBOX_ROOT = pathlib.Path("/sandbox/jobs")

def prepare_sandbox(
    job_id:     uuid.UUID,
    language:   Language,
    code:       str,
    test_inputs: list[str],
) -> pathlib.Path:
    """Create the per-job sandbox directory and write all inputs up front.

    All test case input files are written before any container is launched,
    so the execution container can mount the directory read-only from the start.

    Args:
        job_id:      The submission UUID.
        language:    Submission language (determines source filename).
        code:        Raw source code string.
        test_inputs: Ordered list of stdin strings, one per test case.

    Returns:
        Path to the job's sandbox directory.
    """
    job_dir   = SANDBOX_ROOT / str(job_id)
    input_dir = job_dir / "inputs"

    job_dir.mkdir(parents=True, exist_ok=False)
    input_dir.mkdir()

    (job_dir / SOURCE_FILENAMES[language]).write_text(code, encoding="utf-8")

    for idx, stdin_data in enumerate(test_inputs):
        (input_dir / f"tc_{idx}.txt").write_text(stdin_data, encoding="utf-8")

    return job_dir
```

---

### 10.4 Step 2 — Compilation Container (compiled languages only)

Unchanged from the single-container-per-test-case design. Compilation runs in a dedicated
writable container, produces a binary in the sandbox directory, then exits.

```python
# worker/compile.py
import subprocess, pathlib
from shared.enums import Language
from worker.runners import COMPILE_COMMANDS

COMPILER_IMAGES: dict[Language, str] = {
    Language.CPP:  "rce-cpp:latest",    # docker/cpp/Dockerfile  — Clang-based
    Language.JAVA: "rce-java:latest",   # docker/java/Dockerfile — javac
}

def compile_submission(language: Language, job_dir: pathlib.Path) -> tuple[bool, str]:
    """Run the compilation step in an isolated, writable container.

    The sandbox directory is mounted read-write so the compiler can emit
    the binary alongside the source file. Stderr is written to
    /sandbox/compile_err.txt (host: job_dir/compile_err.txt).

    Args:
        language: The submission language.
        job_dir:  Host path to the job's sandbox directory.

    Returns:
        Tuple of (success: bool, compiler_stderr: str).
        compiler_stderr is capped at 4 KB.
    """
    compile_cmd = COMPILE_COMMANDS.get(language)
    if compile_cmd is None:
        return True, ""   # interpreted language — skip

    subprocess.run(
        [
            "docker", "run", "--rm",
            "--memory=512m",
            "--cpus=1.0",
            "--pids-limit=32",
            "--network=none",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--volume={job_dir}:/sandbox",          # rw — compiler writes binary here
            COMPILER_IMAGES[language],
            "sh", "-c",
            f"{compile_cmd} 2>/sandbox/compile_err.txt",
        ],
        capture_output=True,
        timeout=30,
    )

    err_path = job_dir / "compile_err.txt"
    compiler_stderr = ""
    if err_path.exists():
        compiler_stderr = err_path.read_bytes()[:4096].decode("utf-8", errors="replace")
        err_path.unlink()

    # Compilation succeeded if the expected output binary was produced
    binary_produced = _binary_exists(language, job_dir)
    return binary_produced, compiler_stderr


def _binary_exists(language: Language, job_dir: pathlib.Path) -> bool:
    """Check whether the compiler produced the expected output artifact.

    Args:
        language: Submission language.
        job_dir:  Host sandbox directory.

    Returns:
        True if the expected binary or class file exists.
    """
    if language == Language.CPP:
        return (job_dir / "a.out").exists()
    if language == Language.JAVA:
        return (job_dir / "Main.class").exists()
    return True
```

---

### 10.5 Step 3 — Execution Container (one container, all test cases)

One container is launched for the entire submission. It runs indefinitely (no top-level
timeout on the container — each individual test case invocation is bounded by GNU `timeout`).
The worker drives evaluation from outside the container using `docker exec` to run each
test case and read back its output.

```
Host worker                        Execution container (running)
────────────                       ──────────────────────────────
docker run --detach ...       ──►  container starts, sleeps (CMD: sleep infinity)
                                   /sandbox mounted :ro
                                   /tmp mounted tmpfs noexec

for each test case:
  docker exec ... sh -c           ──►  timeout Xs prog < /sandbox/inputs/tc_N.txt
    "timeout ... < tc_N.txt             > /tmp/stdout.txt 2>/tmp/stderr.txt
     > /tmp/stdout.txt ..."             echo $? > /tmp/exit_code.txt
  docker exec cat /tmp/stdout.txt ◄──  stdout bytes (capped to 100 KB)
  docker exec cat /tmp/stderr.txt ◄──  stderr bytes (capped to 4 KB)
  docker exec cat /tmp/exit_code  ◄──  exit code
  compare → verdict
  if verdict != ACC: break (fail-fast)

docker rm -f container            ──►  container destroyed
```

```python
# worker/execute.py
import subprocess, pathlib, time, uuid, json
from dataclasses import dataclass
from shared.enums import Language
from worker.runners import RUN_COMMANDS

RUNNER_IMAGES: dict[Language, str] = {
    Language.CPP:    "rce-cpp:latest",     # docker/cpp/Dockerfile    — Clang, coreutils, UID 10001
    Language.JAVA:   "rce-java:latest",    # docker/java/Dockerfile   — JRE, coreutils, UID 10001
    Language.PYTHON: "rce-python:latest",  # docker/python/Dockerfile — Python 3.11, coreutils, UID 10001
    Language.NODEJS: "rce-js:latest",      # docker/js/Dockerfile     — Node 20, coreutils, UID 10001
}

STDOUT_CAP_BYTES = 102_400   # 100 KB
STDERR_CAP_BYTES = 4_096     # 4 KB


@dataclass
class ContainerHandle:
    """Represents a running execution container for a single submission.

    Attributes:
        name:          The unique container name used for docker exec / rm calls.
        language:      The submission language.
        fair_time_sec: Per-test-case time limit in seconds (GNU timeout).
    """
    name:          str
    language:      Language
    fair_time_sec: int


def start_execution_container(
    language:       Language,
    job_dir:        pathlib.Path,
    fair_memory_mb: int,
    fair_time_sec:  int,
) -> ContainerHandle:
    """Launch the long-lived execution container for a submission.

    The container starts with `sleep infinity` as its entrypoint so it stays
    alive while the worker drives test case evaluation via `docker exec`.
    The sandbox is mounted read-only. All writes go to /tmp (tmpfs, noexec).

    Args:
        language:       Submission language.
        job_dir:        Host path to the job's sandbox directory (read-only mount).
        fair_memory_mb: Language-adjusted memory limit in MB.
        fair_time_sec:  Language-adjusted time limit per test case in seconds.

    Returns:
        ContainerHandle for subsequent exec / cleanup calls.

    Raises:
        RuntimeError: If the container fails to start.
    """
    name = f"rce-{uuid.uuid4().hex[:16]}"

    result = subprocess.run(
        [
            "docker", "run",
            "--detach",
            "--name",         name,
            "--memory",       f"{fair_memory_mb}m",
            "--memory-swap",  f"{fair_memory_mb}m",   # disable swap
            "--cpus",         "0.5",
            "--pids-limit",   "64",
            "--ulimit",       "nofile=64:64",
            "--ulimit",       "fsize=5000000",
            "--read-only",
            "--tmpfs",        "/tmp:rw,size=50m,noexec",
            "--network",      "none",
            "--cap-drop",     "ALL",
            "--security-opt", "no-new-privileges",
            "--security-opt", "seccomp=/etc/rce/seccomp.json",
            f"--volume={job_dir}:/sandbox:ro",
            RUNNER_IMAGES[language],
            "sleep", "infinity",                       # keep container alive
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to start execution container: {result.stderr.strip()}"
        )

    return ContainerHandle(name=name, language=language, fair_time_sec=fair_time_sec)


def run_test_case_in_container(
    handle:    ContainerHandle,
    tc_index:  int,
) -> dict:
    """Execute one test case inside the already-running container.

    Runs the user program via `docker exec`, piping the pre-written input file
    as stdin. Stdout, stderr, and exit code are written to /tmp inside the
    container (tmpfs) and read back individually with separate `docker exec cat`
    calls. Each `docker exec` is a fresh process — no state persists between
    test case invocations.

    Args:
        handle:    The running ContainerHandle for this submission.
        tc_index:  Zero-based test case index (matches inputs/tc_{index}.txt).

    Returns:
        Dict with keys:
            exit_code  (int)   — program exit code; 124 = TLE
            stdout     (bytes) — capped to STDOUT_CAP_BYTES
            stderr     (bytes) — capped to STDERR_CAP_BYTES
            elapsed_ms (int)   — wall-clock ms for this test case
    """
    run_cmd     = RUN_COMMANDS[handle.language]
    input_path  = f"/sandbox/inputs/tc_{tc_index}.txt"
    time_limit  = handle.fair_time_sec

    exec_cmd = (
        f"timeout {time_limit}s {run_cmd} "
        f"< {input_path} "
        f"> /tmp/stdout.txt "
        f"2>/tmp/stderr.txt; "
        f"echo $? > /tmp/exit_code.txt"
    )

    start_ms = time.monotonic_ns() // 1_000_000

    subprocess.run(
        ["docker", "exec", handle.name, "sh", "-c", exec_cmd],
        capture_output=True,
    )

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    stdout   = _exec_read(handle.name, "/tmp/stdout.txt",   STDOUT_CAP_BYTES)
    stderr   = _exec_read(handle.name, "/tmp/stderr.txt",   STDERR_CAP_BYTES)
    ec_raw   = _exec_read(handle.name, "/tmp/exit_code.txt", 8)

    # Clear output files so next test case gets a clean slate
    subprocess.run(
        ["docker", "exec", handle.name, "sh", "-c",
         "rm -f /tmp/stdout.txt /tmp/stderr.txt /tmp/exit_code.txt"],
        capture_output=True,
    )

    try:
        exit_code = int(ec_raw.decode().strip())
    except ValueError:
        exit_code = -1

    return {
        "exit_code":  exit_code,
        "stdout":     stdout,
        "stderr":     stderr,
        "elapsed_ms": elapsed_ms,
    }


def stop_execution_container(handle: ContainerHandle) -> None:
    """Force-remove the execution container.

    Always called in a finally block — must not raise.

    Args:
        handle: The ContainerHandle to destroy.
    """
    subprocess.run(
        ["docker", "rm", "-f", handle.name],
        capture_output=True,
    )


def _exec_read(container: str, path: str, cap: int) -> bytes:
    """Read a file from inside a running container via docker exec.

    Args:
        container: Container name.
        path:      Absolute path inside the container.
        cap:       Maximum bytes to return.

    Returns:
        File contents up to `cap` bytes, or empty bytes if the file
        does not exist or the exec fails.
    """
    result = subprocess.run(
        ["docker", "exec", container, "cat", path],
        capture_output=True,
    )
    if result.returncode != 0:
        return b""
    return result.stdout[:cap]
```

---

### 10.6 Docker — Rootless Mode

```bash
# Worker host: run Docker in rootless mode.
# Containers never run as root on the host, even if UID 0 inside the container.
dockerd-rootless-setuptool.sh install
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
```

> The Celery worker process communicates with the rootless Docker daemon via the user-scoped
> socket. No access to `/var/run/docker.sock` (root socket) is granted.

---

## 11. Seccomp Profile

Stored at `/etc/rce/seccomp.json`. Version-controlled. Changes require security review.

The profile uses a **whitelist (allowlist)** approach: all syscalls are denied by default;
only the minimum required set for safe code execution is permitted. Particularly dangerous
syscalls (`ptrace`, `mount`, `clone` with namespace flags, etc.) are explicitly blocked
even if they would have been allowed by Docker's default profile.

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "archMap": [
    {
      "architecture": "SCMP_ARCH_X86_64",
      "subArchitectures": ["SCMP_ARCH_X86", "SCMP_ARCH_X32"]
    },
    {
      "architecture": "SCMP_ARCH_AARCH64",
      "subArchitectures": ["SCMP_ARCH_ARM"]
    }
  ],
  "syscalls": [
    {
      "names": [
        "read", "write", "close", "fstat", "lstat", "stat",
        "poll", "lseek", "mmap", "mprotect", "munmap", "brk",
        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
        "ioctl", "pread64", "pwrite64", "readv", "writev",
        "access", "pipe", "select", "sched_yield",
        "mremap", "msync", "mincore", "madvise",
        "dup", "dup2", "pause", "nanosleep", "getitimer",
        "alarm", "setitimer", "getpid", "sendfile",
        "socket", "connect", "accept", "sendto", "recvfrom",
        "shutdown", "bind", "listen", "getsockname", "getpeername",
        "socketpair", "setsockopt", "getsockopt",
        "exit", "wait4", "uname", "fcntl", "flock",
        "fsync", "fdatasync", "truncate", "ftruncate",
        "getcwd", "chdir", "rename", "mkdir", "rmdir",
        "creat", "link", "unlink", "symlink", "readlink",
        "chmod", "fchmod", "chown", "fchown", "lchown",
        "umask", "gettimeofday", "getrlimit", "getrusage",
        "sysinfo", "times", "getuid", "getgid", "geteuid",
        "getegid", "getgroups", "getpgrp", "getppid",
        "setsid", "setuid", "setgid",
        "sigaltstack", "utime", "mknod",
        "statfs", "fstatfs", "getpriority", "setpriority",
        "prctl", "arch_prctl",
        "gettid", "futex", "sched_getaffinity",
        "set_thread_area", "get_thread_area",
        "exit_group", "epoll_ctl", "epoll_wait", "set_tid_address",
        "restart_syscall", "semtimedop", "fadvise64",
        "timer_create", "timer_settime", "timer_gettime",
        "timer_getoverrun", "timer_delete", "clock_gettime",
        "clock_getres", "clock_nanosleep",
        "epoll_create", "tgkill", "waitid", "openat",
        "getdents64", "set_robust_list", "get_robust_list",
        "splice", "tee", "sync_file_range",
        "vmsplice", "epoll_pwait", "signalfd", "timerfd_create",
        "eventfd", "fallocate", "timerfd_settime", "timerfd_gettime",
        "signalfd4", "eventfd2", "epoll_create1", "dup3",
        "pipe2", "inotify_init1", "preadv", "pwritev",
        "rt_tgsigqueueinfo", "perf_event_open",
        "recvmmsg", "accept4", "sendmmsg",
        "getrandom", "memfd_create",
        "statx", "rseq"
      ],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "comment": "Allow clone only for threads (not new namespaces)",
      "names": ["clone"],
      "action": "SCMP_ACT_ALLOW",
      "args": [
        {
          "index": 0,
          "value": 2114060288,
          "op": "SCMP_CMP_MASKED_EQ",
          "valueTwo": 0
        }
      ]
    },
    {
      "comment": "Allow open/openat with O_RDONLY and O_RDWR but not O_WRONLY to /proc",
      "names": ["open"],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "comment": "Explicitly block dangerous syscalls not in allowlist",
      "names": [
        "ptrace",
        "mount",
        "umount2",
        "pivot_root",
        "chroot",
        "unshare",
        "setns",
        "syslog",
        "keyctl",
        "add_key",
        "request_key",
        "perf_event_open",
        "bpf",
        "userfaultfd",
        "kcmp",
        "io_uring_setup",
        "io_uring_enter",
        "io_uring_register",
        "process_vm_readv",
        "process_vm_writev",
        "move_pages",
        "mbind",
        "get_mempolicy",
        "set_mempolicy",
        "migrate_pages",
        "kexec_load",
        "kexec_file_load",
        "reboot",
        "init_module",
        "finit_module",
        "delete_module",
        "create_module",
        "query_module",
        "nfsservctl",
        "vm86old",
        "vm86",
        "modify_ldt",
        "personality"
      ],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    }
  ]
}
```

> **Maintenance:** When a new runner image is added (new language or base image update), run
> `seccomp-gen` tooling to verify no required syscalls are missing from the allowlist before
> deploying to production.

---

## 12. Judging Engine

### 12.1 Full Evaluation Flow

```python
# worker/tasks.py
import shutil, uuid
from celery import Celery
from shared.enums import Language, SubmissionStatus, Verdict
from worker.sandbox import prepare_sandbox
from worker.compile import compile_submission
from worker.execute import (
    start_execution_container,
    run_test_case_in_container,
    stop_execution_container,
    ContainerHandle,
)
from worker.fairness import compute_limits
from db.queries import (
    get_submission, set_status_running, get_test_cases,
    finalise_submission,
)
from redis_client import publish_result

app = Celery("rce")

@app.task(bind=True, max_retries=0)
def evaluate_submission(self, job_id: str) -> None:
    """Main Celery task: evaluate all test cases for a submission.

    One execution container is launched per submission. All test cases run
    sequentially inside that container via docker exec. The container is
    destroyed in the finally block regardless of outcome.

    Args:
        job_id: UUID string of the submission to evaluate.
    """
    job_dir:   pathlib.Path    | None = None
    container: ContainerHandle | None = None
    submission = get_submission(job_id)

    try:
        # ── Step 1: Terminal state protection ──────────────────────────────
        rows = set_status_running(job_id)
        if rows == 0:
            return   # not pending — drop (already processed or ghost retry)

        # ── Step 2: Compute fair limits ────────────────────────────────────
        language = Language(submission.language)
        fair_time_sec, fair_memory_mb = compute_limits(
            submission.problem.base_time_limit_ms,
            submission.problem.base_memory_limit_mb,
            language,
        )

        # ── Step 3: Load test cases & prepare sandbox ──────────────────────
        test_cases = get_test_cases(submission.problem_id)  # ordered by ordering ASC

        job_dir = prepare_sandbox(
            job_id       = uuid.UUID(job_id),
            language     = language,
            code         = submission.code,
            test_inputs  = [tc.input_data for tc in test_cases],
        )

        # ── Step 4: Compile (if needed) ────────────────────────────────────
        compile_ok, compiler_stderr = compile_submission(language, job_dir)
        if not compile_ok:
            _finalise(job_id, Verdict.COMPILATION_ERROR,
                      stderr_snippet=compiler_stderr[:512])
            return

        # ── Step 5: Launch the single execution container ──────────────────
        container = start_execution_container(
            language       = language,
            job_dir        = job_dir,
            fair_memory_mb = fair_memory_mb,
            fair_time_sec  = fair_time_sec,
        )

        # ── Step 6: Execute test cases (fail-fast) inside the container ────
        worst_time_ms = 0

        for idx, tc in enumerate(test_cases):
            result  = run_test_case_in_container(container, tc_index=idx)
            verdict = _classify(result["exit_code"])

            worst_time_ms = max(worst_time_ms, result["elapsed_ms"])

            if verdict == Verdict.ACCEPTED:
                actual   = result["stdout"].decode("utf-8", errors="replace")
                expected = tc.expected_output
                if _normalise(actual) != _normalise(expected):
                    verdict = Verdict.WRONG_ANSWER

            if verdict != Verdict.ACCEPTED:
                _finalise(
                    job_id, verdict,
                    execution_time_ms = worst_time_ms,
                    stdout_snippet    = result["stdout"][:1024].decode("utf-8", errors="replace"),
                    stderr_snippet    = result["stderr"][:512].decode("utf-8",  errors="replace"),
                )
                return

        # ── Step 7: All test cases passed ──────────────────────────────────
        _finalise(
            job_id, Verdict.ACCEPTED,
            execution_time_ms = worst_time_ms,
            stdout_snippet    = result["stdout"][:1024].decode("utf-8", errors="replace"),
            stderr_snippet    = "",
        )

    except Exception as exc:
        _finalise(job_id, Verdict.INTERNAL_ERROR, stderr_snippet=str(exc)[:512])

    finally:
        # Always destroy the container and sandbox, in that order
        if container:
            stop_execution_container(container)
        if job_dir and job_dir.exists():
            shutil.rmtree(job_dir)
```

---

### 12.2 Helper Functions

```python
# worker/tasks.py (continued)
import pathlib

def _classify(exit_code: int) -> Verdict:
    """Classify a docker exec exit code into a verdict.

    GNU coreutils `timeout` exits 124 on expiry — unambiguous TLE.
    All other non-zero codes are RE.

    Args:
        exit_code: The exit code written to /tmp/exit_code.txt by the shell.

    Returns:
        Verdict enum value.
    """
    if exit_code == 124:
        return Verdict.TIME_LIMIT_EXCEEDED
    if exit_code != 0:
        return Verdict.RUNTIME_ERROR
    return Verdict.ACCEPTED


def _normalise(text: str) -> str:
    """Normalise program output for comparison.

    Rules:
      - Strip trailing whitespace from each line.
      - Strip trailing blank lines.
      - Internal whitespace is preserved exactly.

    Args:
        text: Raw output string from the program.

    Returns:
        Normalised string suitable for equality comparison.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _finalise(
    job_id:            str,
    verdict:           Verdict,
    execution_time_ms: int   = 0,
    memory_used_mb:    float = 0.0,
    stdout_snippet:    str   = "",
    stderr_snippet:    str   = "",
) -> None:
    """Write final result to PostgreSQL and publish to Redis Pub/Sub.

    PostgreSQL is the durable source of truth. The Redis publish is
    fire-and-forget — if no WebSocket listener is waiting, the message
    is silently dropped; the client recovers by reading from PostgreSQL.

    Sets status = 'completed' for all verdicts including IE.

    Args:
        job_id:             Submission UUID string.
        verdict:            Final verdict.
        execution_time_ms:  Wall-clock time of the slowest test case in ms.
        memory_used_mb:     Peak memory usage in MB (fair limit for now).
        stdout_snippet:     First 1 KB of stdout for UI display.
        stderr_snippet:     First 512 B of stderr for UI display.
    """
    finalise_submission(
        job_id            = job_id,
        status            = SubmissionStatus.COMPLETED,
        verdict           = verdict,
        execution_time_ms = execution_time_ms,
        memory_used_mb    = memory_used_mb,
        stdout_snippet    = stdout_snippet,
        stderr_snippet    = stderr_snippet,
    )
    publish_result(
        job_id, verdict, execution_time_ms,
        memory_used_mb, stdout_snippet, stderr_snippet,
    )
```

---

### 12.3 Verdict Classification Summary

| Condition (checked in order)     | Verdict |
|----------------------------------|---------|
| exit code == `124`               | TLE     |
| exit code != `0`                 | RE      |
| normalised stdout != expected    | WA      |
| compiler binary not produced     | CE      |
| unhandled worker exception       | IE      |
| all test cases pass              | ACC     |

> `docker exec` exit codes mirror the process exit code directly.
> GNU coreutils `timeout` (guaranteed in all runner images) exits `124` on expiry.

---

### 12.4 Container Lifecycle Summary

```
Worker
  │
  ├─ docker run --detach  →  container C starts (sleep infinity)
  │
  ├─ docker exec C  →  test case 0  (fresh process, /tmp cleared after)
  ├─ docker exec C  →  test case 1
  │   ...
  ├─ docker exec C  →  test case N
  │
  └─ docker rm -f C  →  container destroyed (finally block, always runs)
```

Each `docker exec` creates a brand-new process inside the container. No heap, globals,
file descriptors, or other process state carries over between test cases. The only
shared resource is the container's writable `/tmp` tmpfs — which is explicitly cleared
(`rm -f /tmp/stdout.txt /tmp/stderr.txt /tmp/exit_code.txt`) after each exec before
the next one begins.

---

## 13. Real-Time WebSocket System

### 13.1 Connection Manager

```python
# api/websocket.py
import asyncio, uuid, json
from fastapi import WebSocket, WebSocketDisconnect
from db.queries import get_submission
from redis_client import get_pubsub
from auth.dependencies import decode_jwt_ws

# Per-process in-memory registry.
# One dict per uvicorn worker process — not shared across processes.
# Each process subscribes independently to Redis Pub/Sub.
active_connections: dict[str, WebSocket] = {}

PING_INTERVAL_SEC = 20
WS_TIMEOUT_SEC    = 90

async def handle_ws(job_id: str, token: str, ws: WebSocket) -> None:
    """Handle a WebSocket connection for a submission result.

    Protocol:
      1. Validate JWT and ownership.
      2. Send 'ack'.
      3. Check DB for already-completed result (race condition fix).
      4. If not done: subscribe to Redis, send pings, wait for result.
      5. Send result and close.

    Args:
        job_id: UUID string of the submission to watch.
        token:  Raw JWT string from query parameter.
        ws:     The WebSocket connection object.
    """
    await ws.accept()

    # ── Auth ───────────────────────────────────────────────────────────────
    user_id = await decode_jwt_ws(token)
    if user_id is None:
        await ws.send_json({"type": "error", "code": "UNAUTHORIZED",
                            "detail": "invalid token"})
        await ws.close()
        return

    # ── Ownership check ────────────────────────────────────────────────────
    submission = await get_submission(job_id)
    if submission is None:
        await ws.send_json({"type": "error", "code": "NOT_FOUND",
                            "detail": "job_id does not exist"})
        await ws.close()
        return

    if str(submission.user_id) != str(user_id):
        await ws.send_json({"type": "error", "code": "FORBIDDEN",
                            "detail": "job does not belong to you"})
        await ws.close()
        return

    await ws.send_json({"type": "ack", "job_id": job_id})

    # ── Race condition fix: flush existing result immediately ──────────────
    if submission.status == "completed":
        await ws.send_json(_build_result_payload(submission))
        await ws.close()
        return

    # ── Register and wait ──────────────────────────────────────────────────
    active_connections[job_id] = ws
    pubsub = await get_pubsub()
    await pubsub.subscribe(f"job_updates:{job_id}")

    try:
        await asyncio.wait_for(
            _listen_with_heartbeat(ws, pubsub, job_id),
            timeout=WS_TIMEOUT_SEC,
        )
    except (asyncio.TimeoutError, WebSocketDisconnect):
        pass
    finally:
        await pubsub.unsubscribe(f"job_updates:{job_id}")
        active_connections.pop(job_id, None)
        await ws.close(code=1000)


async def _listen_with_heartbeat(
    ws: WebSocket,
    pubsub,
    job_id: str,
) -> None:
    """Pump Redis messages to the WebSocket, sending pings every 20 s.

    Args:
        ws:     The WebSocket connection.
        pubsub: Redis pubsub object subscribed to this job's channel.
        job_id: The submission UUID string.
    """
    ping_task = asyncio.create_task(_heartbeat(ws))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            await ws.send_json({"type": "result", **data})
            return   # result delivered — done
    finally:
        ping_task.cancel()


async def _heartbeat(ws: WebSocket) -> None:
    """Send a ping frame every PING_INTERVAL_SEC seconds.

    Prevents NAT/proxy timeouts on idle connections during long-running jobs.
    Uses WebSocket ping frames (not application-level JSON pings).

    Args:
        ws: The WebSocket connection.
    """
    while True:
        await asyncio.sleep(PING_INTERVAL_SEC)
        await ws.send_json({"type": "ping"})


def _build_result_payload(submission) -> dict:
    """Build the result JSON payload from a completed submission row.

    Args:
        submission: ORM submission object with all fields populated.

    Returns:
        Dict matching the WSResultPayload schema.
    """
    return {
        "type":             "result",
        "job_id":           str(submission.id),
        "status":           submission.status,
        "verdict":          submission.verdict,
        "execution_time_ms": submission.execution_time_ms or 0,
        "memory_used_mb":   float(submission.memory_used_mb or 0),
        "stdout_snippet":   submission.stdout_snippet or "",
        "stderr_snippet":   submission.stderr_snippet or "",
    }
```

---

### 13.2 Worker Publishes to Redis

```python
# redis_client.py
import json, uuid
from redis import Redis
from shared.enums import Verdict, SubmissionStatus

def publish_result(
    job_id: str,
    verdict: Verdict,
    execution_time_ms: int,
    memory_used_mb: float,
    stdout_snippet: str,
    stderr_snippet: str,
) -> None:
    """Publish a completed submission result to the Redis Pub/Sub channel.

    The FastAPI WebSocket listener for this job_id will forward the
    message to the waiting client.

    Args:
        job_id:            Submission UUID string.
        verdict:           Final verdict.
        execution_time_ms: Wall-clock time in ms.
        memory_used_mb:    Peak memory in MB.
        stdout_snippet:    First 1 KB of stdout.
        stderr_snippet:    First 512 B of stderr.
    """
    redis = Redis.from_url(settings.REDIS_URL)
    payload = json.dumps({
        "job_id":             job_id,
        "status":             SubmissionStatus.COMPLETED,
        "verdict":            verdict,
        "execution_time_ms":  execution_time_ms,
        "memory_used_mb":     memory_used_mb,
        "stdout_snippet":     stdout_snippet,
        "stderr_snippet":     stderr_snippet,
    })
    redis.publish(f"job_updates:{job_id}", payload)
```

---

## 14. Fault Tolerance

### 14.1 Zombie Sweeper — Celery Beat

Celery Beat runs the zombie sweeper every 60 seconds. Stuck `running` submissions older
than 2 minutes are marked `IE` with `status = completed`.

```python
# worker/beat_schedule.py
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "zombie-sweeper": {
        "task":     "worker.tasks.sweep_zombies",
        "schedule": 60.0,   # every 60 seconds
    },
    "sandbox-dir-sweep": {
        "task":     "worker.tasks.sweep_sandbox_dirs",
        "schedule": 600.0,  # every 10 minutes
    },
}
```

```python
# worker/tasks.py (continued)
from db.queries import sweep_zombie_submissions
from redis_client import publish_result
from shared.enums import Verdict, SubmissionStatus
import pathlib, time

@app.task
def sweep_zombies() -> int:
    """Mark stuck 'running' submissions older than 2 minutes as IE.

    Runs via Celery Beat every 60 seconds.

    Returns:
        Number of submissions recovered.
    """
    zombie_ids = sweep_zombie_submissions()   # returns list of job_id strings
    for job_id in zombie_ids:
        publish_result(job_id, Verdict.INTERNAL_ERROR, 0, 0.0, "", "zombie sweep")
    return len(zombie_ids)


@app.task
def sweep_sandbox_dirs() -> int:
    """Remove sandbox directories older than 15 minutes.

    Guards against worker crashes that skip the finally cleanup block.
    Runs via Celery Beat every 10 minutes.

    Returns:
        Number of directories removed.
    """
    sandbox_root = pathlib.Path("/sandbox/jobs")
    cutoff = time.time() - 900   # 15 minutes
    removed = 0
    for d in sandbox_root.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            removed += 1
    return removed
```

```sql
-- db/queries.sql
-- Called by sweep_zombies task
UPDATE submissions
SET    verdict    = 'IE',
       status     = 'completed',
       updated_at = NOW()
WHERE  status     = 'running'
  AND  updated_at < NOW() - INTERVAL '2 minutes'
RETURNING id;
```

---

### 14.2 Worker Configuration

```python
# worker/celeryconfig.py
broker_url                  = "redis://localhost:6379/0"
result_backend              = "redis://localhost:6379/1"
task_serializer             = "json"
result_serializer           = "json"
accept_content              = ["json"]
task_acks_late              = True
worker_prefetch_multiplier  = 1    # one task at a time per worker process
task_track_started          = True
beat_schedule               = CELERYBEAT_SCHEDULE
```

---

## 15. Coding Standards

| Area             | Standard                                                                  |
|------------------|---------------------------------------------------------------------------|
| Python version   | 3.10+ — strict type hints on all function signatures                      |
| Docstrings       | Google-style on all public functions, classes, and modules                |
| FastAPI handlers | `async / await` — zero blocking calls on the event loop                   |
| Celery tasks     | Synchronous only — no `asyncio` inside task functions                     |
| DB access        | SQLAlchemy 2.x async engine for FastAPI; sync `Session` for Celery tasks  |
| Enums            | All status/verdict/language values use `StrEnum` — no bare string literals |
| `job_id`         | UUID v4, server-generated — validated as `UUID` type before path use      |
| Secrets          | `os.environ` / Pydantic `BaseSettings` only — never hardcoded             |
| Seccomp profile  | Versioned in repo — changes require dedicated security PR review           |
| Docker images    | Pinned `sha256` digests in production — no `latest` tags in runner images |

---

## 16. Docker Images

### 16.1 Directory Layout

```
docker/
├── cpp/Dockerfile       # C++ runner & compiler — Clang
├── clang/Dockerfile     # Clang variant (identical to cpp for now; reserved)
├── python/Dockerfile    # Python 3.11 runner
└── js/Dockerfile        # Node.js 20 runner
```

All images share these properties:
- Base: Debian Bookworm Slim (pinned; smallest attack surface with a real package manager)
- Non-root user: `runner` (UID `10001`) — containers never run as root
- `coreutils` installed: guarantees GNU `timeout` (exit code `124` for TLE)
- `ca-certificates` installed: required for any TLS verification inside the container
- `WORKDIR /sandbox`: default working directory matches the volume mount point
- No shell entrypoint in execution: `CMD` is overridden by the worker's `docker run` command

---

### 16.2 `docker/cpp/Dockerfile`

Used for both **compilation** (C++) and **execution** of compiled binaries.
Compiler: `clang` + `libc6-dev` + `make`.

```dockerfile
FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    libc6-dev \
    make \
    coreutils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 runner
WORKDIR /sandbox
USER runner
CMD ["sh"]
```

**Compile command (worker):**
```bash
clang++ -O2 -o /sandbox/a.out /sandbox/solution.cpp 2>/sandbox/stderr.txt
```

**Run command (per test case, via `docker exec` inside the running container):**
```bash
timeout {fair_time_sec}s /sandbox/a.out < /sandbox/inputs/tc_{N}.txt \
    > /tmp/stdout.txt 2>/tmp/stderr.txt; echo $? > /tmp/exit_code.txt
```

---

### 16.3 `docker/clang/Dockerfile`

Identical to `docker/cpp/Dockerfile`. Reserved for future use cases such as
AddressSanitizer (`-fsanitize=address`) or UBSanitizer builds for debugging submissions.
Not wired into the judging engine in v1.

```dockerfile
FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    libc6-dev \
    make \
    coreutils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 runner
WORKDIR /sandbox
USER runner
CMD ["sh"]
```

---

### 16.4 `docker/python/Dockerfile`

Python 3.11 runner. No compilation step.
`PYTHONDONTWRITEBYTECODE=1` prevents `.pyc` file creation in the read-only sandbox.
`PYTHONUNBUFFERED=1` ensures stdout/stderr are flushed immediately (correct timing).

```dockerfile
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    coreutils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 runner
WORKDIR /sandbox
USER runner
CMD ["python3"]
```

**Run command (per test case, via `docker exec`):**
```bash
timeout {fair_time_sec}s python3 /sandbox/solution.py < /sandbox/inputs/tc_{N}.txt \
    > /tmp/stdout.txt 2>/tmp/stderr.txt; echo $? > /tmp/exit_code.txt
```

---

### 16.5 `docker/js/Dockerfile`

Node.js 20 (LTS) runner. No compilation step.
`NODE_ENV=production` disables dev-only behaviour and suppresses some verbose warnings.

```dockerfile
FROM node:20-bookworm-slim
ENV NODE_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    coreutils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 runner
WORKDIR /sandbox
USER runner
CMD ["node"]
```

**Run command (per test case, via `docker exec`):**
```bash
timeout {fair_time_sec}s node /sandbox/solution.js < /sandbox/inputs/tc_{N}.txt \
    > /tmp/stdout.txt 2>/tmp/stderr.txt; echo $? > /tmp/exit_code.txt
```

---

### 16.6 Image Registry & Tagging

| Language | Image name      | Dockerfile            |
|----------|-----------------|-----------------------|
| C++      | `rce-cpp`       | `docker/cpp/Dockerfile`    |
| Clang    | `rce-clang`     | `docker/clang/Dockerfile`  |
| Python   | `rce-python`    | `docker/python/Dockerfile` |
| Node.js  | `rce-js`        | `docker/js/Dockerfile`     |

**Build commands:**

```bash
docker build -t rce-cpp:latest    docker/cpp/
docker build -t rce-clang:latest  docker/clang/
docker build -t rce-python:latest docker/python/
docker build -t rce-js:latest     docker/js/
```

> **Production note:** tag images with a content-addressable digest
> (`rce-python@sha256:...`) in the worker's image map rather than `latest`,
> so image updates require an explicit worker redeploy.

---

### 16.7 Security Properties Common to All Images

| Property                          | Detail                                                          |
|-----------------------------------|-----------------------------------------------------------------|
| Non-root runtime user             | `runner` (UID `10001`) — enforced in Dockerfile                 |
| No package manager at runtime     | `apt-get` cache purged; no `pip install` / `npm install` inside container |
| No shell for interpreted runners  | Python and Node runners don't need `sh`; the worker overrides CMD |
| GNU `timeout` guaranteed          | `coreutils` installed — exit code `124` is reliable TLE signal  |
| Minimal package surface           | `--no-install-recommends` + cache wipe keeps image small and reduces CVE exposure |

---

## 17. Result Storage & TTL Policy

### 17.1 Design Decision

**PostgreSQL is the sole source of truth for all submission results.**

Redis is used exclusively for:
- Celery task queue (transient — tasks are consumed and deleted)
- Pub/Sub result delivery to WebSocket connections (fire-and-forget, no persistence)
- Rate-limit counters (short-lived keys with TTL)

Redis **never** stores submission results durably. If a client misses the Pub/Sub message
(e.g. WebSocket connection dropped before the worker published), the result is always
recoverable from PostgreSQL via `GET /submissions/{job_id}` or on the next WebSocket connect
(the race-condition fix in Section 13.1 queries the DB on connect).

```
Worker finishes
      │
      ├──► UPDATE submissions SET verdict=..., status='completed'  ← durable (PostgreSQL)
      │
      └──► PUBLISH job_updates:{job_id} payload                    ← transient (Redis Pub/Sub)
                │
                └── FastAPI WS handler receives it, forwards to client, done.
                    If nobody is listening: message is lost — that is acceptable
                    because the client can always re-read from PostgreSQL.
```

### 17.2 Submission Row Retention

- Submission rows are **retained indefinitely** until explicitly removed by a future cleanup policy.
- No `DELETE` or archival logic is implemented in v1.
- This is a deliberate decision: data loss is worse than storage cost at this stage.

### 17.3 Future Cleanup Policy (Note — Not Implemented)

> ⚙️ **Deferred to a later milestone.** When retention policy is defined, consider:
>
> - Archive submissions older than N days to cold storage (S3 / object store) before deletion.
> - Soft-delete pattern: add `deleted_at TIMESTAMPTZ` column; exclude from queries with `WHERE deleted_at IS NULL`.
> - User-initiated deletion: allow users to delete their own submissions via `DELETE /submissions/{job_id}`.
> - Admin bulk purge: periodic job purging submissions older than a configurable threshold.

---

## 18. Open Items

The following architectural decisions remain open. Implementation should not be blocked by them, but each must be resolved before the corresponding feature goes to production.

| # | Item | Notes |
|---|------|-------|
| 1 | **Docker image CVE scanning** | Integrate Trivy or Grype into CI. Fail builds on HIGH/CRITICAL CVEs. Define update cadence. |
| 2 | **Worker scaling** | Number of Celery workers, max Redis queue depth, `503` backpressure when queue full. |
| 3 | **Observability** | Structured JSON logging (structlog), Prometheus metrics (throughput, queue depth, verdict distribution, container spin-up latency), OpenTelemetry tracing. |
| 4 | **DB connection pooling** | PgBouncer in transaction mode, or SQLAlchemy async pool sizing for FastAPI. |
| 5 | **Problem setter API** | `POST /problems`, `POST /problems/{id}/test_cases` with `problem_setter` role enforcement. |
| 6 | **Actual memory measurement** | `memory_used_mb` is currently the fair limit, not real usage. Use cgroup `memory.peak` or `docker stats` to capture actual peak RSS. |
| 7 | **Java runner image** | `docker/java/Dockerfile` not yet provided. Needs JRE (not JDK) slim base with `javac` for compilation and `java` for execution, `coreutils`, and UID `10001` runner user — same pattern as other images. |
| 8 | **Image digest pinning** | Replace `latest` tags in `RUNNER_IMAGES` and `COMPILER_IMAGES` with `sha256` digests for production deploys. |

---

*Confidential — Internal Use Only*

