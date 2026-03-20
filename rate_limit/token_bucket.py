"""Token bucket rate limiter (burst control).

Capacity  : 1 token
Refill    : 0.5 tokens / second  (one request every 2 seconds)
Storage   : Redis keys tb:{user_id}:tokens (FLOAT), tb:{user_id}:last_refill (FLOAT unix ts)
Atomicity : Lua script — read-modify-write is race-free.
"""
from __future__ import annotations

import time
import uuid

from fastapi import HTTPException, status

from config.settings import settings
from redis_client import get_async_redis

# ---------------------------------------------------------------------------
# Lua script — evaluated atomically server-side
# ---------------------------------------------------------------------------
_LUA_TOKEN_BUCKET = """
local tokens_key     = KEYS[1]
local last_refill_key = KEYS[2]
local capacity       = tonumber(ARGV[1])
local refill_rate    = tonumber(ARGV[2])
local now            = tonumber(ARGV[3])

local tokens      = tonumber(redis.call('GET', tokens_key))
local last_refill = tonumber(redis.call('GET', last_refill_key))

if tokens == nil then
    tokens      = capacity
    last_refill = now
end

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

if tokens < 1 then
    -- Not enough tokens — compute seconds until one token is available
    local wait = (1 - tokens) / refill_rate
    redis.call('SET', tokens_key, tokens, 'EX', 120)
    redis.call('SET', last_refill_key, now, 'EX', 120)
    return {0, tostring(wait)}
end

tokens = tokens - 1
redis.call('SET', tokens_key, tokens, 'EX', 120)
redis.call('SET', last_refill_key, now, 'EX', 120)
return {1, '0'}
"""


async def check_token_bucket(user_id: uuid.UUID) -> None:
    """Consume one token. Raises HTTP 429 if the bucket is empty."""
    redis = await get_async_redis()
    uid = str(user_id)
    tokens_key = f"tb:{uid}:tokens"
    last_refill_key = f"tb:{uid}:last_refill"
    now = time.time()

    result = await redis.eval(
        _LUA_TOKEN_BUCKET,
        2,
        tokens_key,
        last_refill_key,
        settings.TOKEN_BUCKET_CAPACITY,
        settings.TOKEN_BUCKET_REFILL_RATE,
        now,
    )

    allowed, wait_str = result
    if not allowed:
        retry_after = max(1, int(float(wait_str)) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Submission rate limit exceeded (burst)",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Policy": "token-bucket",
            },
        )
