"""Celery tasks: evaluate_submission, sweep_zombies, sweep_sandbox_dirs."""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

import redis as _redis_sync
from celery import Task
from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.settings import settings
from db.sync_session import get_sync_db
from shared.enums import Verdict
from worker.app import app
from worker.compile import run_compile_container
from worker.execute import ExecResult, exec_test_case, launch_exec_container, teardown_container
from worker.fairness import compute_fair_limits
from worker.runners import LANGUAGE_CONFIG
from worker.sandbox import cleanup_sandbox, prepare_sandbox

_redis = _redis_sync.from_url(settings.REDIS_URL, decode_responses=True)

F = TypeVar("F", bound=Callable[..., object])


def _typed_task(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    return cast(Callable[[F], F], app.task(*args, **kwargs))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    """Strip trailing whitespace per line and remove trailing blank lines."""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _evaluate_output(
    exit_code: int, stdout: str, expected: str, delimiter: str
) -> tuple[Verdict, str, str | None]:
    if exit_code == 124:
        return Verdict.TLE, stdout, None

    if delimiter not in stdout:
        return Verdict.RE, stdout, None

    parts = stdout.split(delimiter)
    stdout_snippet = parts[0]
    engine_eval_str = parts[1].strip()

    try:
        engine_eval = json.loads(engine_eval_str)
        expected_json = json.loads(expected)

        if engine_eval == expected_json:
            return Verdict.ACC, stdout_snippet, engine_eval_str
        else:
            return Verdict.WA, stdout_snippet, engine_eval_str
    except (json.JSONDecodeError, ValueError):
        return Verdict.RE, stdout_snippet, engine_eval_str


def _finalise(
    job_id: str,
    verdict: Verdict,
    exec_time_ms: int,
    memory_mb: int,
    stdout_snippet: str,
    stderr_snippet: str,
    passed_cases: int = 0,
    total_cases: int = 0,
    failed_tc_id: Any | None = None,
    actual: str | None = None,
    expected: str | None = None,
) -> None:
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
                    stderr_snippet = :stderr_snippet,
                    passed_test_cases = :passed,
                    total_test_cases = :total,
                    failed_test_case_id = :failed_id,
                    actual_output = :actual,
                    expected_output = :expected
                WHERE id = :job_id
            """),
            {
                "verdict": verdict.value,
                "exec_time_ms": exec_time_ms,
                "memory_mb": memory_mb,
                "stdout_snippet": stdout_snippet[:1024],
                "stderr_snippet": stderr_snippet[:512],
                "passed": passed_cases,
                "total": total_cases,
                "failed_id": failed_tc_id,
                "actual": actual,
                "expected": expected,
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
        "passed_test_cases": passed_cases,
        "total_test_cases": total_cases,
        "failed_test_case_id": str(failed_tc_id) if failed_tc_id else None,
        "actual_output": actual,
        "expected_output": expected,
    }
    _redis.publish(f"job_updates:{job_id}", json.dumps(payload))


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------


@_typed_task(bind=True, max_retries=0, name="worker.tasks.evaluate_submission")
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
    job_dir: Path | None = None

    try:
        print(f"Starting evaluation for submission {job_id}", flush=True)
        # --- 1. Atomic pending → running ---
        with get_sync_db() as db:
            transition_result = cast(
                CursorResult[Any],
                db.execute(
                    text(
                        "UPDATE submissions SET status='running' WHERE id=:id AND status='pending' RETURNING id"
                    ),
                    {"id": job_id},
                ),
            )
            if transition_result.rowcount == 0:
                print(f"Submission {job_id} is already running or completed — dropping task")
                return
            
            submission_row = db.execute(
                text("SELECT language, code, problem_id, is_submit FROM submissions WHERE id=:id"),
                {"id": job_id},
            ).fetchone()
            if submission_row is None:
                _finalise(job_id, Verdict.IE, 0, 0, "", "Submission not found")
                return
            language, code, problem_id, is_submit = (
                submission_row.language,
                submission_row.code,
                submission_row.problem_id,
                submission_row.is_submit,
            )

            problem_row = db.execute(
                text("SELECT base_time_limit_ms, base_memory_limit_mb FROM problems WHERE id=:id"),
                {"id": problem_id},
            ).fetchone()
            if problem_row is None:
                _finalise(job_id, Verdict.IE, 0, 0, "", "Problem not found")
                return

            # Load test cases: samples only for Run, all for Submit
            tc_query = "SELECT id, input_data, expected_output FROM test_cases WHERE problem_id=:pid"
            if not is_submit:
                tc_query += " AND is_sample=TRUE"
            tc_query += " ORDER BY ordering ASC"

            test_cases = db.execute(text(tc_query), {"pid": problem_id}).fetchall()
            if not test_cases:
                _finalise(job_id, Verdict.IE, 0, 0, "", "No test cases found for problem")
                return

            config_row = db.execute(
                text(
                    "SELECT driver_code FROM problem_language_configs WHERE problem_id=:pid AND language=:lang"
                ),
                {"pid": problem_id, "lang": getattr(language, "value", language)},
            ).fetchone()

            if config_row is None:
                _finalise(
                    job_id, Verdict.IE, 0, 0, "", "Language configuration not found for problem"
                )
                return

        # --- 2. Compute fair limits ---
        limits = compute_fair_limits(
            language, problem_row.base_time_limit_ms, problem_row.base_memory_limit_mb
        )

        # --- 3. Runner config ---
        runner = LANGUAGE_CONFIG[language]
        print(
            f"Evaluating submission {job_id} (is_submit={is_submit}) with language={language}"
        )

        # --- 4. Prepare sandbox ---
        delimiter = f"---RCE_EXEC_{job_id}---"
        secure_driver = config_row.driver_code.replace("{job_id}", str(job_id))
        final_code = f"{code}\n\n{secure_driver}"

        job_dir = prepare_sandbox(
            job_id=job_id,
            source_code=final_code,
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
                ce_err = (job_dir / "compile_err.txt").read_text(encoding="utf-8")[:1024]
                _finalise(job_id, Verdict.CE, 0, limits.memory_mb, "", ce_err)
                return

        # --- 6. Launch execution container ---
        container_name = launch_exec_container(
            job_dir=job_dir, image=image, memory_mb=limits.memory_mb
        )

        # --- 7. Execute & Evaluate ---
        verdict = Verdict.ACC
        passed_cases = 0
        total_cases = len(test_cases)
        failed_tc_id = None
        actual_output = None
        expected_output = None
        last_stdout = ""
        last_stderr = ""
        run_details = []

        start_time = time.monotonic()

        for idx, tc in enumerate(test_cases):
            exec_result = exec_test_case(
                container_name=container_name,
                run_cmd=runner.run_cmd,
                test_case_index=idx,
                time_sec=limits.time_sec,
            )
            last_stdout = exec_result.stdout
            last_stderr = exec_result.stderr

            tc_verdict, stdout_snip, engine_actual = _evaluate_output(
                exec_result.exit_code, exec_result.stdout, tc.expected_output, delimiter
            )

            if tc_verdict == Verdict.ACC:
                passed_cases += 1
            
            if not is_submit:
                # Path A: Run Code (Full evaluation)
                run_details.append({
                    "test_case_id": str(tc.id),
                    "verdict": tc_verdict.value,
                    "actual": engine_actual,
                    "expected": tc.expected_output
                })
            else:
                # Path B: Submit Code (Fail-Fast)
                if tc_verdict != Verdict.ACC:
                    verdict = tc_verdict
                    failed_tc_id = tc.id
                    actual_output = engine_actual
                    expected_output = tc.expected_output
                    last_stdout = stdout_snip
                    break

        exec_time_ms = int((time.monotonic() - start_time) * 1000)

        if not is_submit:
            # For Path A, verdict is "Finished" or similar, but we'll use ACC if all passed
            if passed_cases < total_cases:
                verdict = Verdict.WA
            # Use stdout_snippet to pass back the run_details as JSON
            stdout_snip = json.dumps(run_details)
        else:
            stdout_snip = last_stdout

        # --- 8. Finalise ---
        _finalise(
            job_id=job_id,
            verdict=verdict,
            exec_time_ms=exec_time_ms,
            memory_mb=limits.memory_mb,
            stdout_snippet=stdout_snip,
            stderr_snippet=last_stderr,
            passed_cases=passed_cases,
            total_cases=total_cases,
            failed_tc_id=failed_tc_id,
            actual=actual_output,
            expected=expected_output
        )
        print(f"Finalised evaluation for submission {job_id}")

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


@_typed_task(name="worker.tasks.sweep_zombies")
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


@_typed_task(name="worker.tasks.sweep_sandbox_dirs")
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
