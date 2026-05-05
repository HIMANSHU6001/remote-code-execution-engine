"""Compilation container runner.

Runs a short-lived Docker container to compile C++ / Java source code.
The compiled artifact is written back into the shared sandbox directory.
Compilation Error (CE) is detected by checking for the expected artifact.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from worker.sandbox import get_host_path

_COMPILE_TIMEOUT_SEC = 30


# Docker flags shared by compilation containers
_COMPILE_FLAGS = [
    "--rm",
    "--memory=512m",
    "--cpus=1.0",
    "--pids-limit=32",
    "--network=none",
    "--security-opt=no-new-privileges",
    "--user=root",
]


def run_compile_container(
    job_dir: Path,
    image: str,
    compile_cmd: str,
    compile_artifact: str,
) -> bool:
    """Run the compilation container and return True if successful.

    The compile container mounts job_dir read-write so the compiler can
    write its output artifact (a.out / Main.class) back to the host.

    Args:
        job_dir: Absolute path to the per-job sandbox directory on the host.
        image: Docker image name (e.g. 'rce-cpp:latest').
        compile_cmd: Shell command to run inside the container.
        compile_artifact: Filename expected after successful compilation.

    Returns:
        True if the artifact exists after compilation, False on CE.
    """
    host_volume_path = get_host_path(job_dir)
    cmd = [
        "docker",
        "run",
        *_COMPILE_FLAGS,
        f"--volume={host_volume_path}:/sandbox",
        image,
        "sh",
        "-c",
        f"{compile_cmd} 2>/sandbox/compile_err.txt",
    ]

    try:
        subprocess.run(cmd, timeout=_COMPILE_TIMEOUT_SEC, check=False)
    except subprocess.TimeoutExpired:
        return False

    return (job_dir / compile_artifact).exists()
