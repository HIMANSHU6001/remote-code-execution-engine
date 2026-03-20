"""Celery tasks: evaluate_submission, sweep_zombies, sweep_sandbox_dirs."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from celery import Task
from sqlalchemy import text

from config.settings import settings
from db.sync_session import get_sync_db
from shared.enums import Verdict
from worker.app import app
from worker.compile import run_compile_container
from worker.execute import ExecResult, exec_test_case, launch_exec_container, teardown_container
from worker.fairness import compute_fair_limits
from worker.runners import LANGUAGE_CONFIG
from worker.sandbox import cleanup_sandbox, prepare_sandbox

import redis as _redis_sync

_redis = _redis_sync.from_url(settings.REDIS_URL, decode_responses=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Strip trailing whitespace per line and remove trailing blank lines."""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _classify_verdict(exit_code: int, stdout: str, expected: str) -> Verdict:
    if exit_code == 124:
        return Verdict.TLE
    if exit_code != 0:
        return Verdict.RE
    if _normalise(stdout) != _normalise(expected):
        return Verdict.WA
    return Verdict.ACC


def _finalise(job_id: str, verdict: Verdict, exec_time_ms: int, memory_mb: int,
              stdout_snippet: str, stderr_snippet: str) -> None:
    """Write final result to PostgreSQL and publish to Redis Pub/Sub."""
    with get_sync_db() as db:
        db.execute(
            text("""
                UPDATE submissions
                SET status = 'completed',
                    verdict = :verdict,
                    execution_time_ms = :exec_time_ms,
                    memory_used_mb = :memory_mb,
                    stdout_snippet = :stdout_snippet,
                    stderr_snippet = :stderr_snippet
                WHERE id = :job_id
            """),
            {
                "verdict": verdict.value,
                "exec_time_ms": exec_time_ms,
                "memory_mb": memory_mb,
                "stdout_snippet": stdout_snippet[:1024],
                "stderr_snippet": stderr_snippet[:512],
                "job_id": job_id,
            },
        )

    payload = {
        "job_id": job_id,
        "status": "completed",
        "verdict": verdict.value,
        "execution_time_ms": exec_time_ms,
        "memory_used_mb": memory_mb,
        "stdout_snippet": stdout_snippet[:1024],
        "stderr_snippet": stderr_snippet[:512],
    }
    _redis.publish(f"job_updates:{job_id}", json.dumps(payload))


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------

@app.task(bind=True, max_retries=0, name="worker.tasks.evaluate_submission")
def evaluate_submission(self: Task, job_id: str) -> None:
    """Evaluate all test cases for a submission and record the verdict.

    Steps:
    1. Atomic pending → running transition (idempotency guard)
    2. Compute fair limits per language
    3. Load all test cases (ordered by ordering ASC)
    4. Prepare sandbox directory
    5. Compile (C++ / Java only) → CE on failure
    6. Launch execution container
    7. Execute test cases fail-fast
    8. Finalise (DB write + Redis publish)
    9. Cleanup (always in finally)
    """
    container_name: str | None = None
    job_dir = None

    try:
        # --- 1. Atomic pending → running ---
        with get_sync_db() as db:
            result = db.execute(
                text("UPDATE submissions SET status='running' WHERE id=:id AND status='pending' RETURNING id"),
                {"id": job_id},
            )
            if result.rowcount == 0:
                return  # already running or completed — drop task

            row = db.execute(
                text("SELECT language, code, problem_id FROM submissions WHERE id=:id"),
                {"id": job_id},
            ).fetchone()
            language, code, problem_id = row.language, row.code, row.problem_id

            prob = db.execute(
                text("SELECT base_time_limit_ms, base_memory_limit_mb FROM problems WHERE id=:id"),
                {"id": problem_id},
            ).fetchone()

            test_cases = db.execute(
                text("SELECT id, input_data, expected_output FROM test_cases WHERE problem_id=:pid ORDER BY ordering ASC"),
                {"pid": problem_id},
            ).fetchall()

        # --- 2. Compute fair limits ---
        limits = compute_fair_limits(language, prob.base_time_limit_ms, prob.base_memory_limit_mb)

        # --- 3. Runner config ---
        runner = LANGUAGE_CONFIG[language]

        # --- 4. Prepare sandbox ---
        job_dir = prepare_sandbox(
            job_id=job_id,
            source_code=code,
            source_filename=runner.source_file,
            test_inputs=[tc.input_data for tc in test_cases],
        )

        image = f"rce-{language}:latest"

        # --- 5. Compile (if needed) ---
        if runner.compile_cmd:
            success = run_compile_container(
                job_dir=job_dir,
                image=image,
                compile_cmd=runner.compile_cmd,
                compile_artifact=runner.compile_artifact,
            )
            if not success:
                ce_err = ""
                err_file = job_dir / "compile_err.txt"
                if err_file.exists():
                    ce_err = err_file.read_text(encoding="utf-8", errors="replace")[:settings.COMPILE_ERR_CAP_BYTES]
                _finalise(job_id, Verdict.CE, 0, limits.memory_mb, "", ce_err)
                return

        # --- 6. Launch execution container ---
        container_name = launch_exec_container(job_dir=job_dir, image=image, memory_mb=limits.memory_mb)

        # --- 7. Execute test cases (fail-fast) ---
        verdict = Verdict.ACC
        last_result: ExecResult | None = None
        total_time_ms = 0
        start = time.monotonic()

        for idx, tc in enumerate(test_cases):
            result = exec_test_case(
                container_name=container_name,
                run_cmd=runner.run_cmd,
                test_case_index=idx,
                time_sec=limits.time_sec,
            )
            last_result = result
            tc_verdict = _classify_verdict(result.exit_code, result.stdout, tc.expected_output)
            if tc_verdict != Verdict.ACC:
                verdict = tc_verdict
                break

        total_time_ms = int((time.monotonic() - start) * 1000)

        stdout_snip = last_result.stdout if last_result else ""
        stderr_snip = last_result.stderr if last_result else ""

        # --- 8. Finalise ---
        _finalise(job_id, verdict, total_time_ms, limits.memory_mb, stdout_snip, stderr_snip)

    except Exception:
        _finalise(job_id, Verdict.IE, 0, 0, "", "Internal error")
        raise

    finally:
        # --- 9. Cleanup ---
        if container_name:
            teardown_container(container_name)
        if job_dir:
            cleanup_sandbox(job_dir)


# ---------------------------------------------------------------------------
# Periodic tasks (Celery Beat)
# ---------------------------------------------------------------------------

@app.task(name="worker.tasks.sweep_zombies")
def sweep_zombies() -> None:
    """Mark 'running' submissions stuck for > 2 minutes as IE (zombie sweep).

    Runs every 60 seconds via Celery Beat.
    """
    with get_sync_db() as db:
        result = db.execute(
            text("""
                UPDATE submissions
                SET verdict = 'IE', status = 'completed'
                WHERE status = 'running'
                  AND updated_at < NOW() - INTERVAL '2 minutes'
                RETURNING id
            """)
        )
        zombie_ids = [str(r.id) for r in result.fetchall()]

    for job_id in zombie_ids:
        payload = json.dumps({"job_id": job_id, "status": "completed", "verdict": "IE"})
        _redis.publish(f"job_updates:{job_id}", payload)


@app.task(name="worker.tasks.sweep_sandbox_dirs")
def sweep_sandbox_dirs() -> None:
    """Remove sandbox job directories older than 15 minutes.

    Runs every 10 minutes via Celery Beat.
    """
    base = Path(settings.SANDBOX_BASE_DIR)
    if not base.exists():
        return

    cutoff = time.time() - 900  # 15 minutes
    for job_dir in base.iterdir():
        if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
            shutil.rmtree(job_dir, ignore_errors=True)
