"""Multi-language fairness engine.

C++ is the baseline. All limits are computed from the problem's base values
using per-language multipliers so that all participants have an equal
opportunity to solve the problem regardless of language choice.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from shared.enums import Language


@dataclass(frozen=True)
class FairLimits:
    time_sec: int      # wall-clock seconds passed to `timeout` command
    memory_mb: int     # --memory and --memory-swap value for Docker


# (time_multiplier, memory_multiplier, memory_offset_mb)
_MULTIPLIERS: dict[str, tuple[float, float, int]] = {
    Language.CPP:    (1.0, 1.0,  0),
    Language.JAVA:   (2.0, 1.5, 100),
    Language.PYTHON: (5.0, 1.5,  20),
    Language.NODEJS: (3.0, 1.3,  30),
}


def compute_fair_limits(language: str, base_time_ms: int, base_memory_mb: int) -> FairLimits:
    """Return time and memory limits adjusted for the given language.

    Args:
        language: One of the Language enum values.
        base_time_ms: Problem's base time limit in milliseconds (C++ baseline).
        base_memory_mb: Problem's base memory limit in megabytes (C++ baseline).

    Returns:
        FairLimits with integer values safe to pass directly to Docker / timeout.
    """
    time_mul, mem_mul, mem_offset = _MULTIPLIERS.get(language, (1.0, 1.0, 0))
    fair_time_sec = math.ceil((base_time_ms * time_mul) / 1000)
    fair_memory_mb = math.floor(base_memory_mb * mem_mul) + mem_offset
    return FairLimits(time_sec=fair_time_sec, memory_mb=fair_memory_mb)
