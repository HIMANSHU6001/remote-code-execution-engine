"""Sandbox directory management.

All input files are written to the host filesystem BEFORE the execution
container is launched. The container mounts the job directory read-only.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

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
    try:
        shutil.rmtree(job_dir, ignore_errors=True)
    except Exception:
        pass  # best-effort; sweep_sandbox_dirs will catch stragglers
