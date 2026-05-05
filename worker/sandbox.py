"""Sandbox directory management.

All input files are written to the host filesystem BEFORE the execution
container is launched. The container mounts the job directory read-only.
"""

from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path, PurePosixPath

from config.settings import settings


def prepare_sandbox(
    job_id: str,
    source_code: str,
    source_filename: str,
    test_inputs: list[str],
) -> Path:
    """Create the per-job sandbox directory and populate it.

    Layout::

        /sandbox/jobs/{job_id}/
        ├── solution.{ext}     (or Main.java / solution.js)
        └── inputs/
            ├── tc_0.txt
            ├── tc_1.txt
            └── ...

    Returns the Path to the job directory.
    """
    job_dir = Path(settings.SANDBOX_BASE_DIR) / job_id
    inputs_dir = job_dir / "inputs"
    job_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(exist_ok=True)

    # Write source file
    (job_dir / source_filename).write_text(source_code, encoding="utf-8")

    # Write each test case input
    for idx, input_data in enumerate(test_inputs):
        (inputs_dir / f"tc_{idx}.txt").write_text(input_data, encoding="utf-8")

    return job_dir


def cleanup_sandbox(job_dir: Path) -> None:
    """Remove the job directory tree. Called in the task's finally block."""
    with contextlib.suppress(Exception):
        shutil.rmtree(job_dir, ignore_errors=True)


def get_host_path(job_dir: Path) -> str:
    """Translate a container-side job directory path to the host-side path for Docker.

    When the worker runs inside a Docker container (Docker-in-Docker), it sees paths like
    '/sandbox/jobs/...' or '/app/docker/sandbox/...'. However, the Docker daemon (on the host)
    needs the absolute path on the HOST filesystem to perform volume mounts.
    """
    host_root = os.environ.get("HOST_PROJECT_ROOT")
    if not host_root:
        # Fallback for local non-docker development
        return str(job_dir).replace("\\", "/")

    host_root = host_root.replace("\\", "/").rstrip("/")

    host_sandbox_root = os.environ.get("HOST_SANDBOX_ROOT")
    if host_sandbox_root:
        host_sandbox_root = host_sandbox_root.replace("\\", "/").rstrip("/")
    else:
        host_sandbox_root = f"{host_root}/docker/sandbox"

    job_dir_str = str(job_dir).replace("\\", "/")
    # relative_job_path handles cases where job_dir is under /app (the project root inside worker)
    relative_job_path = job_dir_str.replace("/app/", "").lstrip("/")

    job_dir_posix = PurePosixPath(job_dir_str)
    sandbox_base_posix = PurePosixPath(settings.SANDBOX_BASE_DIR)
    try:
        sandbox_rel = job_dir_posix.relative_to(sandbox_base_posix)
        return f"{host_sandbox_root}/{sandbox_rel.as_posix()}"
    except ValueError:
        return f"{host_root}/{relative_job_path}"
