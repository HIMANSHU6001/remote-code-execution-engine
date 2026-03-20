"""Rate limiting package.

Applies two independent limiters on every POST /submit in order:
1. Token bucket  — burst control    (1 req / 2 s per user)
2. Sliding window — sustained ceiling (10 req / 60 s per user)
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from rate_limit.sliding_window import check_sliding_window
from rate_limit.token_bucket import check_token_bucket


async def apply_rate_limits(user_id: uuid.UUID) -> None:
    """Run both limiters in sequence. Raises 429 if either limit is exceeded."""
    await check_token_bucket(user_id)
    await check_sliding_window(user_id)
