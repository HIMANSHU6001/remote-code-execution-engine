"""Execution container orchestration (Isolated Driver Architecture)."""

import logging
import secrets
import subprocess
from pathlib import Path

from worker.sandbox import get_host_path

logger = logging.getLogger(__name__)

def execute_driver_code(
    job_dir: Path,
    image: str,
    run_cmd: list[str],
    memory_mb: int,
    timeout_sec: int = 10,
) -> tuple[bool, str]:
    """
    Launches a Docker container to run the user's code and our driver script ONCE.
    The driver script internally handles test case iteration and writes run_results.json.
    
    Returns:
        tuple[bool, str]: (Success boolean, Error message if the container crashed)
    """
    host_volume_path = get_host_path(job_dir)
    local_seccomp_path = "/app/infra/seccomp.json"

    # Generate a unique name so we can force-kill it if it times out
    name = f"rce-{secrets.token_hex(8)}"
    
    cmd = [
        "docker", "run",
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
        # CRITICAL: This MUST be rw so the driver can write run_results.json
        f"--volume={host_volume_path}:/sandbox:rw", 
        image,
    ] + run_cmd  # run_cmd is e.g. ["node", "/sandbox/solution.js"]

    logger.info(f"Launching execution container: {name} | CMD: {' '.join(run_cmd)}")

    success = False
    error_msg = ""

    try:
        # Run the container and wait for it to exit
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        
        if result.returncode == 0:
            success = True
        else:
            # If return code is not 0, there was a fatal compilation or syntax error
            error_msg = f"Fatal Error: {result.stderr.strip()}"
            logger.warning(f"Container {name} crashed. {error_msg}")
            
    except subprocess.TimeoutExpired:
        error_msg = f"Time Limit Exceeded (Global hard timeout of {timeout_sec}s hit)"
        logger.error(f"Container {name} hit infinite loop. Force killing.")
        
    finally:
        # Always clean up the container, whether it succeeded, crashed, or timed out
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)

    return success, error_msg