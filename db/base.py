"""Async SQLAlchemy engine and Redis connection for the FastAPI process."""

from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as redis # Ensure you have 'redis' installed in your requirements.txt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings

# --- 1. Database Configuration (SQLAlchemy) ---
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


# --- 2. Redis Configuration ---

# We create a connection pool that persists for the lifetime of the FastAPI process
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL, 
    decode_responses=True, # Critical: so we get strings instead of bytes
    max_connections=20
)

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI dependency — yields an async Redis client."""
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        # Closes the specific client instance (returning it to the pool)
        await client.close()