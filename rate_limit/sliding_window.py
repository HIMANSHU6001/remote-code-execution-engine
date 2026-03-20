"""Sliding window counter rate limiter (sustained ceiling).

Limit  : 10 submissions per 60 seconds per user
Storage: Redis sorted set  sw:{user_id}  (score = unix timestamp)
Atomicity: Lua script — ZREMRANGEBYSCORE + ZCARD + ZADD is race-free.
"""
from __future__ import annotations

import time
import uuid

from fastapi import HTTPException, status

from config.settings import settings
from redis_client import get_async_redis

_LUA_SLIDING_WINDOW = """
local key        = KEYS[1]
local now        = tonumber(ARGV[1])
local window     = tonumber(ARGV[2])
local max_count  = tonumber(ARGV[3])
local expire_ttl = tonumber(ARGV[4])

local cutoff = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)

local count = tonumber(redis.call('ZCARD', key))
if count >= max_count then
    local oldest = tonumber(redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2])
    local reset_in = math.ceil(oldest + window - now)
    return {0, tostring(count), tostring(reset_in)}
end

redis.call('ZADD', key, now, tostring(now) .. '-' .. tostring(math.random(1e9)))
redis.call('EXPIRE', key, expire_ttl)
return {1, tostring(count + 1), '0'}
"""


async def check_sliding_window(user_id: uuid.UUID) -> None:
    """Record this request. Raises HTTP 429 if the window limit is exceeded."""
    redis = await get_async_redis()
    key = f"sw:{user_id}"
    now = time.time()
    window = settings.SLIDING_WINDOW_SEC
    max_count = settings.SLIDING_WINDOW_MAX

    result = await redis.eval(
        _LUA_SLIDING_WINDOW,
        1,
        key,
        now,
        window,
        max_count,
        window + 10,
    )

    allowed, count_str, reset_str = result
    if not allowed:
        reset_in = max(1, int(reset_str))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Submission rate limit exceeded (sustained)",
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Limit": str(max_count),
                "X-RateLimit-Window": str(window),
                "X-RateLimit-Reset": str(int(now) + reset_in),
                "X-RateLimit-Policy": "sliding-window",
            },
        )
