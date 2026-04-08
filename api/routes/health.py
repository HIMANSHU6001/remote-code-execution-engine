from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from redis_client import get_async_redis

router = APIRouter()


@router.get("/health", tags=["health"])
@router.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", tags=["health"], response_model=None)
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict | JSONResponse:
    checks: dict[str, str] = {}
    ready = True

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error:{exc.__class__.__name__}"
        ready = False

    try:
        redis = await get_async_redis()
        if await redis.ping():
            checks["redis"] = "ok"
        else:
            checks["redis"] = "error:no_pong"
            ready = False
    except Exception as exc:
        checks["redis"] = f"error:{exc.__class__.__name__}"
        ready = False

    payload = {"status": "ok" if ready else "degraded", "checks": checks}
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload