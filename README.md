# RCE & Online Judge

A highly secure, asynchronous Remote Code Execution engine and Online Judge platform.

Submissions are sandboxed inside rootless Docker containers with seccomp allowlists, no network, read-only filesystems, and strict CPU/memory/PID limits.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Local Development Setup](#local-development-setup)
6. [Running the Services](#running-the-services)
7. [Environment Variables](#environment-variables)
8. [API Reference](#api-reference)
9. [Fern Documentation and SDKs](#fern-documentation-and-sdks)
10. [Database ERD Generation](#database-erd-generation)
11. [Quick Test with curl](#quick-test-with-curl)
12. [Adding a New Language](#adding-a-new-language)
13. [Code Style](#code-style)

---

## Architecture

```text
Client
  │── POST /submit ─────────────────► FastAPI Gateway
  │◄── 202 { job_id } ───────────────┤
  │                                  │── enqueue ──► Redis (Celery queue)
  │── WS /ws/{job_id}?token=<jwt> ──►│                      │
  │◄── result (via pub/sub) ─────────│◄── publish ──────── Celery Worker
                                     │                      │
                                     └──── r/w ───► PostgreSQL + Docker (rootless)
```

| Component | Technology | Role |
| --- | --- | --- |
| API Gateway | FastAPI | HTTP endpoints, WebSocket hub, rate limiting, auth |
| Message Broker | Redis DB 0 | Celery task queue, Pub/Sub result delivery, rate-limit counters |
| Result Backend | Redis DB 1 | Celery result backend |
| Worker | Celery + Celery Beat | Background code evaluation; periodic zombie/sandbox sweeper |
| Database | PostgreSQL | Persistent storage — problems, test cases, submissions |
| Sandbox | Docker (rootless) | Isolated, resource-capped code execution |

---

## Tech Stack

- **Python 3.10+** throughout
- **FastAPI** — async HTTP + WebSocket
- **SQLAlchemy 2.x** — async ORM for FastAPI, sync session for Celery
- **Alembic** — database migrations
- **Celery 5** + **Celery Beat** — task queue and periodic tasks
- **Redis** — broker, result backend, pub/sub, rate-limit counters
- **PostgreSQL 16** — primary datastore
- **Docker (rootless)** — sandbox execution
- **Pydantic v2** — request/response validation and settings
- **PyJWT** — HS256 JWT authentication

---

## Project Structure

```text
.
├── api/                    # FastAPI process
│   ├── main.py             # App factory and router mounts
│   ├── routes/
│   │   ├── submit.py       # POST /submit
│   │   ├── submissions.py  # GET /submissions/{job_id}
│   │   └── problems.py     # GET /problems/{problem_id}
│   └── websocket.py        # WS /ws/{job_id}
│
├── auth/
│   └── dependencies.py     # JWT decode FastAPI dependency
│
├── rate_limit/
│   ├── __init__.py         # apply_rate_limits() — runs both limiters
│   ├── token_bucket.py     # Burst: 1 req / 2 s (Lua, atomic)
│   └── sliding_window.py   # Sustained: 10 req / 60 s (Lua, atomic)
│
├── db/
│   ├── base.py             # Async SQLAlchemy engine (FastAPI)
│   ├── sync_session.py     # Sync SQLAlchemy session (Celery)
│   ├── models.py           # ORM table definitions
│   ├── queries.py          # Async query helpers
│   └── migrations/         # Alembic migrations
│       └── versions/
│           └── 0001_initial_schema.py
│
├── worker/                 # Celery process
│   ├── app.py              # Celery app instance
│   ├── celeryconfig.py     # Broker, backend, task settings
│   ├── beat_schedule.py    # Periodic task schedule
│   ├── tasks.py            # evaluate_submission, sweep_zombies, sweep_sandbox_dirs
│   ├── sandbox.py          # Host sandbox directory management
│   ├── compile.py          # Compilation container runner
│   ├── execute.py          # Execution container orchestration
│   ├── fairness.py         # Per-language time/memory multipliers
│   └── runners.py          # Language config (source file, compile cmd, run cmd)
│
├── shared/
│   ├── enums.py            # Language, SubmissionStatus, Verdict
│   └── models.py           # Pydantic request/response models
│
├── config/
│   └── settings.py         # Pydantic BaseSettings (reads from .env)
│
├── docker/                 # Sandbox language images
│   ├── cpp/Dockerfile
│   ├── clang/Dockerfile
│   ├── java/Dockerfile
│   ├── python/Dockerfile
│   └── js/Dockerfile
│
├── infra/
│   └── seccomp.json        # Seccomp allowlist (deploy to /etc/rce/seccomp.json on worker host)
│
├── scripts/
│   ├── build_images.sh     # Build all rce-* Docker images
│   └── migrate.sh          # Run alembic upgrade head
│
├── redis_client.py         # Shared async + sync Redis helpers
├── alembic.ini
├── docker-compose.yml      # Local dev: postgres + redis + api + worker + beat
└── pyproject.toml
```

---

## Prerequisites

| Tool | Minimum Version | Notes |
| --- | --- | --- |
| Python | 3.10 | Use pyenv or system Python |
| Docker | 24.x | Rootless mode required for the worker in production; standard mode fine for local dev |
| PostgreSQL | 16 | Provided via docker-compose |
| Redis | 7 | Provided via docker-compose |

---

## Local Development Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd remote-code-execution-engine

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```dotenv
DATABASE_URL=postgresql+asyncpg://rce:rce_secret@localhost:5432/rce
SYNC_DATABASE_URL=postgresql+psycopg2://rce:rce_secret@localhost:5432/rce
REDIS_URL=redis://localhost:6379/0
REDIS_RESULT_URL=redis://localhost:6379/1
JWT_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

### 4. Start infrastructure (PostgreSQL + Redis)

```bash
docker-compose up -d postgres redis
```

Wait for both to be healthy:

```bash
docker-compose ps
```

### 5. Run database migrations

```bash
bash scripts/migrate.sh
# or directly: python -m alembic upgrade head
```

### 6. Build sandbox Docker images

```bash
bash scripts/build_images.sh
```

This builds `rce-cpp`, `rce-java`, `rce-python`, and `rce-js` images locally. Required before the worker can execute any submission.

---

## Running the Services

You need three processes running simultaneously. Open a terminal for each.

### API server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Celery worker

```bash
celery -A worker.app worker --loglevel=info --concurrency=4
```

### Celery Beat (periodic tasks)

```bash
celery -A worker.app beat --loglevel=info
```

Beat runs two periodic tasks:

- `sweep_zombies` — every 60 s: marks stuck `running` submissions as `IE`
- `sweep_sandbox_dirs` — every 10 min: removes stale `/sandbox/jobs/*` directories

### Or run everything via docker-compose

```bash
docker-compose up --build
```

> Note: The `worker` service in docker-compose needs access to the Docker socket and the sandbox volume. Review `docker-compose.yml` and adjust the socket path to match your system before using this in production.

### Production Docker images

Use dedicated production Dockerfiles to avoid dev dependencies and reload mode:

```bash
docker build -f Dockerfile.api.prod -t rce-api:prod .
docker build -f Dockerfile.worker.prod -t rce-worker:prod .
```

`Dockerfile.api` and `Dockerfile.worker` remain optimized for local development.

---

## Environment Variables

All variables are read via `config/settings.py` (Pydantic BaseSettings). See `.env.example` for the full list.

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | — | Async PostgreSQL DSN (`postgresql+asyncpg://...`) |
| `SYNC_DATABASE_URL` | — | Sync PostgreSQL DSN (`postgresql+psycopg2://...`) |
| `REDIS_URL` | `redis://localhost:6379/0` | Broker, pub/sub, rate-limit counters |
| `REDIS_RESULT_URL` | `redis://localhost:6379/1` | Celery result backend |
| `JWT_SECRET` | — | HS256 signing secret — **generate a strong random value** |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `SANDBOX_BASE_DIR` | `/sandbox/jobs` | Host path for per-job sandbox directories |
| `WS_TIMEOUT_SEC` | `90` | WebSocket connection timeout |
| `PING_INTERVAL_SEC` | `20` | WebSocket ping interval |
| `TOKEN_BUCKET_CAPACITY` | `1.0` | Rate limit burst capacity |
| `TOKEN_BUCKET_REFILL_RATE` | `0.5` | Tokens refilled per second (= 1 req / 2 s) |
| `SLIDING_WINDOW_MAX` | `10` | Max submissions per window |
| `SLIDING_WINDOW_SEC` | `60` | Sliding window duration in seconds |
| `STDOUT_CAP_BYTES` | `102400` | Max stdout captured per test case (100 KB) |
| `STDERR_CAP_BYTES` | `4096` | Max stderr captured per test case (4 KB) |
| `COMPILE_ERR_CAP_BYTES` | `4096` | Max compile error captured (4 KB) |

---

## API Reference

Most endpoints require a JWT Bearer token: `Authorization: Bearer <token>`.

Public auth endpoints:

- `POST /api/auth/signup`
- `GET /api/auth/verify?token=...`
- `POST /api/auth/login`

Service-auth endpoint (requires S2S Bearer token):

- `POST /api/auth/social`

Health endpoints:

- `GET /health` and `GET /health/live` (liveness)
- `GET /health/ready` (readiness: DB + Redis checks)

### `POST /submit`

Submit code for evaluation.

**Request body:**

```json
{
  "problem_id": "uuid",
  "language": "python | cpp | java | nodejs",
  "code": "print('hello')"
}
```

**Response `202`:**

```json
{ "job_id": "uuid" }
```

**Error codes:** `401` unauthorized · `404` problem not found · `422` validation error · `429` rate limited

---

### `GET /submissions/{job_id}`

Poll submission status. Returns `status: "running"` with null verdict fields while in progress.

**Response `200`:**

```json
{
  "job_id": "uuid",
  "status": "pending | running | completed",
  "verdict": "ACC | WA | TLE | MLE | RE | CE | IE | null",
  "execution_time_ms": 123,
  "memory_used_mb": 32.0,
  "stdout_snippet": "...",
  "stderr_snippet": "..."
}
```

**Error codes:** `403` (other user's submission) · `404` not found

---

### `WS /ws/{job_id}?token=<jwt>`

Real-time result delivery. The JWT is passed as a query parameter (browser WebSocket limitation).

**Message sequence:**

```text
server → { "type": "ack",    "job_id": "..." }
server → { "type": "ping" }                        # every 20 s
server → { "type": "result", "job_id": "...", "verdict": "ACC", ... }
         (connection closes after result is sent)
```

Connection times out after 90 s. Recover by polling `GET /submissions/{job_id}`.

---

### `GET /problems/{problem_id}`

Fetch problem details and **sample** test cases. Hidden test cases are never returned.

**Response `200`:**

```json
{
  "id": "uuid",
  "title": "Two Sum",
  "base_time_limit_ms": 1000,
  "base_memory_limit_mb": 256,
  "sample_test_cases": [
    { "id": "uuid", "input_data": "2\n1 2", "expected_output": "3", "is_sample": true }
  ]
}
```

---

## Fern Documentation and SDKs

Fern is configured in the `fern/` directory and uses `fern/openapi.yml` as the API contract.

Hosted docs endpoint:

- https://rce-docs.docs.buildwithfern.com

### Install Fern CLI

```bash
npm install -g fern-api
```

### Validate Fern configuration

```bash
cd fern
fern check
```

### Generate SDKs locally

```bash
cd fern
fern generate --group local
```

Generated SDK outputs:

- `sdks/typescript`

### Notes

- HTTP endpoints are modeled in OpenAPI and used by Fern for SDK generation.
- WebSocket behavior (`WS /ws/{job_id}`) is intentionally documented in markdown/API reference prose and not modeled as an OpenAPI path.

---

## Database ERD Generation

Generate the latest ERD from SQLAlchemy models and overwrite the SVG:

```bash
uv run generate-erd
```

Outputs:

- `docs/db-erd.mmd`
- `docs/ERD.svg`

Equivalent direct script command:

```bash
python scripts/generate_erd_svg.py
```

---

## Quick Test with curl

```bash
# 1. Generate a test JWT (adjust JWT_SECRET to match your .env)
TOKEN=$(python -c "
import jwt, datetime
print(jwt.encode(
    {'sub': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'role': 'user',
     'iat': datetime.datetime.utcnow(),
     'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
    'YOUR_JWT_SECRET', algorithm='HS256'
))
")

# 2. Submit code
curl -s -X POST http://localhost:8000/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"problem_id":"<uuid>","language":"python","code":"print(input())"}' | jq .

# 3. Poll result
curl -s http://localhost:8000/submissions/<job_id> \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## Verdict Reference

| Verdict | Meaning |
| --- | --- |
| `ACC` | Accepted — all test cases passed |
| `WA` | Wrong Answer |
| `TLE` | Time Limit Exceeded (GNU `timeout` exit code 124) |
| `MLE` | Memory Limit Exceeded (OOM kill) |
| `RE` | Runtime Error (non-zero exit, not TLE) |
| `CE` | Compilation Error (compiled artifact not produced) |
| `IE` | Internal Error (unhandled worker exception or zombie timeout) |

---

## Adding a New Language

1. **Create a Dockerfile** in `docker/<lang>/Dockerfile`. Follow the existing pattern: `debian:bookworm-slim` base, install runtime + `coreutils` (for GNU `timeout`), create `runner` user UID `10001`.

2. **Register the runner config** in `worker/runners.py`:

   ```python
   Language.YOURLANG: RunnerConfig(
       source_file="solution.ext",
       compile_cmd=None,          # or a compile command
       compile_artifact=None,     # or expected output filename
       run_cmd="your-runtime /sandbox/solution.ext",
   ),
   ```

3. **Add the enum value** to `shared/enums.py` → `Language`.

4. **Add a DB migration** for the new enum value in `language_enum` in PostgreSQL.

5. **Build the image:**

   ```bash
   docker build -t rce-yourlang:latest docker/yourlang/
   ```

6. **Add fairness multipliers** in `worker/fairness.py` → `_MULTIPLIERS`.

---

## Code Style

```bash
# Lint + format
ruff check .
ruff format .

# Type checking
mypy .
```

All code targets **Python 3.10+**, uses strict type hints, and follows Google-style docstrings. Import order is enforced by ruff (`I` rule set).
