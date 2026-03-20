"""Execution container orchestration.

One execution container is launched per submission (sleep infinity).
Individual test cases are driven via `docker exec` calls, reusing the
same container to avoid per-test-case container startup overhead.
"""
from __future__ import annotations

import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


_SECCOMP_PROFILE = "/etc/rce/seccomp.json"


def launch_exec_container(
    job_dir: Path,
    image: str,
    memory_mb: int,
) -> str:
    """Start a long-lived execution container and return its name.

    The container runs `sleep infinity` and stays alive while the worker
    drives individual test cases via `docker exec`.
    """
    name = f"rce-{secrets.token_hex(8)}"
    cmd = [
        "docker", "run", "--detach",
        f"--name={name}",
        f"--memory={memory_mb}m",
        f"--memory-swap={memory_mb}m",   # disable swap
        "--cpus=0.5",
        "--pids-limit=64",
        "--ulimit=nofile=64:64",
        "--ulimit=fsize=5000000",
        "--read-only",
        "--tmpfs=/tmp:rw,size=50m,noexec",
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--security-opt=seccomp={_SECCOMP_PROFILE}",
        f"--volume={job_dir}:/sandbox:ro",
        image,
        "sleep", "infinity",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return name


def exec_test_case(
    container_name: str,
    run_cmd: str,
    test_case_index: int,
    time_sec: int,
) -> ExecResult:
    """Execute one test case inside the running container.

    Uses GNU `timeout` for wall-clock enforcement. After execution reads
    stdout/stderr/exit_code from /tmp and cleans up for the next test case.
    """
    input_path = f"/sandbox/inputs/tc_{test_case_index}.txt"
    exec_cmd = (
        f"timeout {time_sec} {run_cmd} < {input_path} "
        f"> /tmp/stdout.txt 2>/tmp/stderr.txt; echo $? > /tmp/exit_code.txt"
    )

    subprocess.run(
        ["docker", "exec", container_name, "sh", "-c", exec_cmd],
        check=False,
    )

    def _read(path: str, cap: int) -> str:
        out = subprocess.run(
            ["docker", "exec", container_name, "cat", path],
            capture_output=True, text=True,
        )
        return out.stdout[:cap]

    stdout = _read("/tmp/stdout.txt", settings.STDOUT_CAP_BYTES)
    stderr = _read("/tmp/stderr.txt", settings.STDERR_CAP_BYTES)
    exit_code_raw = _read("/tmp/exit_code.txt", 16).strip()
    exit_code = int(exit_code_raw) if exit_code_raw.isdigit() else 1

    # Clean up temp files for the next test case
    subprocess.run(
        ["docker", "exec", container_name, "rm", "-f",
         "/tmp/stdout.txt", "/tmp/stderr.txt", "/tmp/exit_code.txt"],
        check=False,
    )

    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


def teardown_container(container_name: str) -> None:
    """Force-remove the execution container. Called in the task's finally block."""
    subprocess.run(["docker", "rm", "-f", container_name], check=False, capture_output=True)
