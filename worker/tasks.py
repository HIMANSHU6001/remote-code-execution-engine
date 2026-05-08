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
from worker.execute import exec_test_case, launch_exec_container, teardown_container
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


def _evaluate_output(
    exit_code: int, raw_stdout: str, expected: str, delimiter: str
) -> tuple[Verdict, str, str | None]:
    """Parse a single test-case execution result.

    Returns:
        (verdict, user_logs, parsed_actual)
        - user_logs:     Everything the user printed BEFORE the delimiter (capped later).
        - parsed_actual: The raw JSON string the driver printed AFTER the delimiter,
                         or None when the delimiter / JSON parse failed.
    """
    # TLE: the timeout wrapper killed the process
    if exit_code == 124:
        return Verdict.TLE, raw_stdout, None

    # Delimiter missing → driver never reached its print statement
    if delimiter not in raw_stdout:
        return Verdict.RE, raw_stdout, None

    parts = raw_stdout.split(delimiter, maxsplit=1)
    user_logs = parts[0]
    engine_eval_str = parts[1].strip()

    # JSON parse gate — if the driver output is garbled, it's a Runtime Error
    try:
        engine_eval = json.loads(engine_eval_str)
    except (json.JSONDecodeError, ValueError):
        return Verdict.RE, user_logs, engine_eval_str

    try:
        expected_json = json.loads(expected)
    except (json.JSONDecodeError, ValueError):
        # Bad expected_output in the DB — treat as Internal Error
        return Verdict.IE, user_logs, engine_eval_str

    if engine_eval == expected_json:
        return Verdict.ACC, user_logs, engine_eval_str
    else:
        return Verdict.WA, user_logs, engine_eval_str


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
    # Sanitise: strip whitespace noise, collapse empty to None
    clean_stdout = stdout_snippet.strip()[:1000] if stdout_snippet else None
    if not clean_stdout:
        clean_stdout = None
    clean_stderr = stderr_snippet.strip()[:512] if stderr_snippet else None
    if not clean_stderr:
        clean_stderr = None

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
                "stdout_snippet": clean_stdout,
                "stderr_snippet": clean_stderr,
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
        "stdout_snippet": clean_stdout,
        "stderr_snippet": clean_stderr,
        "passed_test_cases": passed_cases,
        "total_test_cases": total_cases,
        "failed_test_case_id": str(failed_tc_id) if failed_tc_id else None,
        "actual_output": actual,
        "expected_output": expected,
    }
    _redis.publish(f"job_updates:{job_id}", json.dumps(payload))


def _finalise_run(
    job_id: str,
    verdict: Verdict,
    exec_time_ms: int,
    memory_mb: int,
    stdout_snippet: str,
    stderr_snippet: str,
    passed_cases: int,
    total_cases: int,
    details: list[dict],
) -> None:
    """Finalise a Run Code execution.

    Golden Rule: actual_output / expected_output / failed_test_case_id are
    NEVER written to the database for Run Code.  The per-test-case detail
    array is published via Redis Pub/Sub only so the API can relay it to the
    connected WebSocket client.
    """
    # Sanitise: strip whitespace noise, collapse empty to None
    clean_stdout = stdout_snippet.strip()[:1000] if stdout_snippet else None
    if not clean_stdout:
        clean_stdout = None
    clean_stderr = stderr_snippet.strip()[:512] if stderr_snippet else None
    if not clean_stderr:
        clean_stderr = None

    # DB: save verdict + counters, but NOT per-TC outputs
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
                    total_test_cases = :total
                WHERE id = :job_id
            """),
            {
                "verdict": verdict.value,
                "exec_time_ms": exec_time_ms,
                "memory_mb": memory_mb,
                "stdout_snippet": clean_stdout,
                "stderr_snippet": clean_stderr,
                "passed": passed_cases,
                "total": total_cases,
                "job_id": job_id,
            },
        )

    # Redis: include the full details array for real-time UI
    payload = {
        "job_id": job_id,
        "status": "completed",
        "verdict": verdict.value,
        "execution_time_ms": exec_time_ms,
        "memory_used_mb": memory_mb,
        "stdout_snippet": clean_stdout,
        "stderr_snippet": clean_stderr,
        "passed_test_cases": passed_cases,
        "total_test_cases": total_cases,
        "details": details,
    }
    _redis.publish(f"job_updates:{job_id}", json.dumps(payload))


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------


@_typed_task(bind=True, max_retries=0, name="worker.tasks.evaluate_submission")
def evaluate_submission(self: Task, job_id: str) -> None:
    """Evaluate test cases for a submission.

    Architecture:
      Path A (Run Code, is_submit=False):
        - Evaluate SAMPLE test cases only.
        - Do NOT fail-fast — run every sample.
        - Return a details array via Redis (never saved to DB).

      Path B (Submit Code, is_submit=True):
        - Evaluate ALL test cases (samples + hidden).
        - Fail-fast on first mismatch.
        - On WA: store the single failed TC's actual/expected in DB.
        - On AC: leave actual_output / expected_output as NULL.
    """
    container_name: str | None = None
    job_dir: Path | None = None

    try:
        # --- 1. Atomic pending → running ---
        with get_sync_db() as db:
            transition_result = cast(
                CursorResult[Any],
                db.execute(
                    text(
                        "UPDATE submissions SET status='running' "
                        "WHERE id=:id AND status='pending' RETURNING id"
                    ),
                    {"id": job_id},
                ),
            )

            if transition_result.rowcount == 0:
                print(f"Submission {job_id} already running or completed — dropping task")
                return

            db.commit()

            submission_row = db.execute(
                text("SELECT language, code, problem_id, is_submit FROM submissions WHERE id=:id"),
                {"id": job_id},
            ).fetchone()
            if submission_row is None:
                _finalise(job_id, Verdict.IE, 0, 0, "", "Submission not found")
                return

            language = submission_row.language
            code = submission_row.code
            problem_id = submission_row.problem_id
            is_submit: bool = submission_row.is_submit

            problem_row = db.execute(
                text("SELECT base_time_limit_ms, base_memory_limit_mb FROM problems WHERE id=:id"),
                {"id": problem_id},
            ).fetchone()
            if problem_row is None:
                _finalise(job_id, Verdict.IE, 0, 0, "", "Problem not found")
                return

            # Test-case filter: samples only for Run, all for Submit
            tc_query = (
                "SELECT id, input_data, expected_output FROM test_cases WHERE problem_id=:pid"
            )
            if not is_submit:
                tc_query += " AND is_sample=TRUE"
            tc_query += " ORDER BY ordering ASC"

            test_cases = db.execute(text(tc_query), {"pid": problem_id}).fetchall()
            if not test_cases:
                _finalise(job_id, Verdict.IE, 0, 0, "", "No test cases found for problem")
                return

            config_row = db.execute(
                text(
                    "SELECT driver_code FROM problem_language_configs "
                    "WHERE problem_id=:pid AND language=:lang"
                ),
                {"pid": problem_id, "lang": getattr(language, "value", language)},
            ).fetchone()
            if config_row is None:
                _finalise(job_id, Verdict.IE, 0, 0, "", "No language config for problem")
                return

        # --- 2. Compute fair limits ---
        limits = compute_fair_limits(
            language, problem_row.base_time_limit_ms, problem_row.base_memory_limit_mb
        )

        # --- 3. Runner config ---
        runner = LANGUAGE_CONFIG[language]
        print(f"Evaluating {job_id} (is_submit={is_submit}, lang={language})")

        # --- 4. Prepare sandbox ---
        delimiter = f"---RCE_EXEC_{job_id}---"
        secure_driver = config_row.driver_code.replace("{job_id}", str(job_id))

        if "{user_code}" in secure_driver:
            final_code = secure_driver.replace("{user_code}", code)
        else:
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
                ce_file = job_dir / "compile_err.txt"
                ce_err = ""
                if ce_file.exists():
                    ce_err = ce_file.read_text(encoding="utf-8", errors="replace")[:1024]
                _finalise(job_id, Verdict.CE, 0, limits.memory_mb, "", ce_err)
                return

        # --- 6. Launch execution container ---
        container_name = launch_exec_container(
            job_dir=job_dir, image=image, memory_mb=limits.memory_mb
        )

        # --- 7. Execute & Evaluate (split-path) ---
        total_cases = len(test_cases)
        passed_cases = 0
        user_logs_parts: list[str] = []  # collect user debug prints
        last_stderr = ""
        start_time = time.monotonic()

        if is_submit:
            # =============================================================
            # PATH B: Submit Code — Fail-Fast
            # =============================================================
            verdict = Verdict.ACC
            failed_tc_id = None
            actual_for_db: str | None = None
            expected_for_db: str | None = None

            for idx, tc in enumerate(test_cases):
                exec_result = exec_test_case(
                    container_name=container_name,
                    run_cmd=runner.run_cmd,
                    test_case_index=idx,
                    time_sec=limits.time_sec,
                )
                last_stderr = exec_result.stderr

                tc_verdict, user_log, parsed_actual = _evaluate_output(
                    exec_result.exit_code,
                    exec_result.stdout,
                    tc.expected_output,
                    delimiter,
                )
                user_logs_parts.append(user_log)

                if tc_verdict == Verdict.ACC:
                    passed_cases += 1
                else:
                    # FAIL-FAST: record the single failure and break
                    verdict = tc_verdict
                    failed_tc_id = tc.id
                    actual_for_db = json.dumps(json.loads(parsed_actual)) if parsed_actual else None
                    expected_for_db = tc.expected_output
                    break

            exec_time_ms = int((time.monotonic() - start_time) * 1000)
            combined_user_logs = "\n".join(user_logs_parts)

            _finalise(
                job_id=job_id,
                verdict=verdict,
                exec_time_ms=exec_time_ms,
                memory_mb=limits.memory_mb,
                stdout_snippet=combined_user_logs,
                stderr_snippet=last_stderr,
                passed_cases=passed_cases,
                total_cases=total_cases,
                failed_tc_id=failed_tc_id,
                # Golden Rule: AC → NULL, WA → single failed TC
                actual=actual_for_db,
                expected=expected_for_db,
            )

        else:
            # =============================================================
            # PATH A: Run Code — Full Evaluation (no fail-fast)
            # =============================================================
            details: list[dict] = []
            verdict = Verdict.ACC

            for idx, tc in enumerate(test_cases):
                exec_result = exec_test_case(
                    container_name=container_name,
                    run_cmd=runner.run_cmd,
                    test_case_index=idx,
                    time_sec=limits.time_sec,
                )
                last_stderr = exec_result.stderr

                tc_verdict, user_log, parsed_actual = _evaluate_output(
                    exec_result.exit_code,
                    exec_result.stdout,
                    tc.expected_output,
                    delimiter,
                )
                user_logs_parts.append(user_log)

                if tc_verdict == Verdict.ACC:
                    passed_cases += 1

                details.append(
                    {
                        "test_case_id": str(tc.id),
                        "input": tc.input_data,
                        "expected": tc.expected_output,
                        "actual": parsed_actual,
                        "verdict": tc_verdict.value,
                    }
                )

            if passed_cases < total_cases:
                verdict = Verdict.WA

            exec_time_ms = int((time.monotonic() - start_time) * 1000)
            combined_user_logs = "\n".join(user_logs_parts)

            # Golden Rule: do NOT write actual/expected to DB for Run Code
            _finalise_run(
                job_id=job_id,
                verdict=verdict,
                exec_time_ms=exec_time_ms,
                memory_mb=limits.memory_mb,
                stdout_snippet=combined_user_logs,
                stderr_snippet=last_stderr,
                passed_cases=passed_cases,
                total_cases=total_cases,
                details=details,
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
