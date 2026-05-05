"""Execution container orchestration.

One execution container is launched per submission (sleep infinity).
Individual test cases are driven via `docker exec` calls, reusing the
same container to avoid per-test-case container startup overhead.
"""

from __future__ import annotations

import logging
import os
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from config.settings import settings

from worker.sandbox import get_host_path

# Use proper logging instead of print
logger = logging.getLogger(__name__)


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
    """Start a long-lived execution container and return its name."""

    host_volume_path = get_host_path(job_dir)

    local_seccomp_path = "/app/infra/seccomp.json"

    name = f"rce-{secrets.token_hex(8)}"
    cmd = [
        "docker",
        "run",
        "--detach",
        f"--name={name}",
        f"--memory={memory_mb}m",
        f"--memory-swap={memory_mb}m",
        "--cpus=0.5",
        "--pids-limit=64",
        "--ulimit=nofile=256:256",
        "--ulimit=fsize=5000000",
        "--read-only",
        "--tmpfs=/tmp:rw,size=50m,noexec",
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--security-opt=seccomp={local_seccomp_path}",
        f"--volume={host_volume_path}:/sandbox:ro",
        image,
        "sleep",
        "infinity",
    ]

    logger.info(
        "Launching execution container: %s image=%s host_volume=%s memory_mb=%s",
        name,
        image,
        host_volume_path,
        memory_mb,
    )

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        time.sleep(0.5)

        inspect_cmd = ["docker", "inspect", "-f", "{{.State.Status}}", name]
        status = subprocess.run(
            inspect_cmd, check=True, capture_output=True, text=True
        ).stdout.strip()

        if status != "running":
            logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr

            subprocess.run(["docker", "rm", "-f", name], capture_output=True)

            raise RuntimeError(
                f"Container died instantly. Status: {status}. Container Logs: {logs}"
            )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        logger.error(
            "Docker run failed. returncode=%s cmd=%s stdout=%s stderr=%s",
            e.returncode,
            " ".join(cmd),
            stdout,
            stderr,
        )
        raise RuntimeError(f"Docker daemon rejected the container launch.\nSTDERR: {stderr}") from e

    return name


def exec_test_case(
    container_name: str,
    run_cmd: str,
    test_case_index: int,
    time_sec: int,
) -> ExecResult:
    """Execute one test case inside the running container."""
    input_path = f"/sandbox/inputs/tc_{test_case_index}.txt"
    exec_cmd = (
        f"timeout {time_sec} {run_cmd} < {input_path} "
        f"> /tmp/stdout.txt 2>/tmp/stderr.txt; echo $? > /tmp/exit_code.txt"
    )

    docker_cmd = ["docker", "exec", container_name, "sh", "-c", exec_cmd]
    logger.info(f"Executing TC {test_case_index} in {container_name}")

    try:
        # Capture the result of the docker exec command
        result = subprocess.run(docker_cmd, check=False, capture_output=True, text=True)

        # TELEMETRY UPGRADE 1: If the shell itself spits out an error, log it!
        if result.stderr:
            logger.error(f"NATIVE DOCKER EXEC STDERR: {result.stderr.strip()}")

    except Exception as e:
        logger.error(f"Failed to execute test case via docker exec: {str(e)}")
        raise

    def _read(path: str, cap: int) -> str:
        out = subprocess.run(
            ["docker", "exec", container_name, "cat", path],
            capture_output=True,
            text=True,
        )
        # TELEMETRY UPGRADE 2: If cat fails (e.g., the file was never created), log the reason
        if out.returncode != 0:
            logger.warning(f"Could not read {path} from container: {out.stderr.strip()}")
        return out.stdout[:cap]

    stdout = _read("/tmp/stdout.txt", settings.STDOUT_CAP_BYTES)
    stderr = _read("/tmp/stderr.txt", settings.STDERR_CAP_BYTES)
    exit_code_raw = _read("/tmp/exit_code.txt", 16).strip()
    exit_code = int(exit_code_raw) if exit_code_raw.isdigit() else 1

    # Clean up temp files for the next test case
    subprocess.run(
        [
            "docker",
            "exec",
            container_name,
            "rm",
            "-f",
            "/tmp/stdout.txt",
            "/tmp/stderr.txt",
            "/tmp/exit_code.txt",
        ],
        check=False,
    )

    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


def teardown_container(container_name: str) -> None:
    """Force-remove the execution container."""
    subprocess.run(["docker", "rm", "-f", container_name], check=False, capture_output=True)
