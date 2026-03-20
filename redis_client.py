"""Shared Redis client helpers — used by both the FastAPI process and Celery worker.

FastAPI uses the async client; Celery uses the sync client from redis-py directly.
This module provides:
  - get_async_redis()  — returns a cached async Redis client (coredis / redis.asyncio)
  - publish_result()   — fire-and-forget publish to a job's Pub/Sub channel (sync)
"""
from __future__ import annotations

import json
from functools import lru_cache

import redis.asyncio as aioredis
import redis as _redis_sync

from config.settings import settings


# ---------------------------------------------------------------------------
# Async client — FastAPI & WebSocket handler
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_async_redis_cached() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_async_redis() -> aioredis.Redis:
    """Return the shared async Redis client (DB 0)."""
    return _get_async_redis_cached()


# ---------------------------------------------------------------------------
# Sync client — Celery worker
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_sync_redis() -> _redis_sync.Redis:
    return _redis_sync.from_url(settings.REDIS_URL, decode_responses=True)


def publish_result(job_id: str, payload: dict) -> None:
    """Publish a completed job result to the Redis Pub/Sub channel.

    Fire-and-forget: if no WebSocket listener is subscribed the message is
    silently dropped. Clients recover via GET /submissions/{job_id}.
    """
    channel = f"job_updates:{job_id}"
    _get_sync_redis().publish(channel, json.dumps(payload))
