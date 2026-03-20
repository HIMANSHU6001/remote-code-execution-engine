"""WS /ws/{job_id} — real-time result delivery via Redis Pub/Sub."""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from auth.dependencies import get_current_user
from config.settings import settings
from db.base import AsyncSessionLocal
from db.queries import get_submission
from redis_client import get_async_redis
from shared.models import WSAckPayload, WSErrorPayload, WSPingPayload, WSResultPayload

router = APIRouter()

# In-process registry — one entry per connected client in this uvicorn worker.
# Not shared across workers; each subscribes to Redis Pub/Sub independently.
active_connections: dict[str, WebSocket] = {}


async def _send_json(ws: WebSocket, payload: dict) -> None:
    await ws.send_text(json.dumps(payload))


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(ws: WebSocket, job_id: uuid.UUID, token: str) -> None:
    """WebSocket endpoint for real-time submission result delivery.

    Protocol:
    1. Accept connection
    2. Validate JWT from query param ?token=<jwt>
    3. Ownership check against DB
    4. Send ack
    5. If already completed → send result and close
    6. Otherwise subscribe Redis Pub/Sub; send pings every PING_INTERVAL_SEC
    7. On result message → send result and close
    8. On WS_TIMEOUT_SEC timeout or client disconnect → clean up
    """
    await ws.accept()
    job_id_str = str(job_id)
    active_connections[job_id_str] = ws

    redis = await get_async_redis()
    pubsub = redis.pubsub()

    try:
        # --- Auth ---
        try:
            from fastapi.security import HTTPAuthorizationCredentials
            user_id = await get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            )
        except Exception:
            await _send_json(ws, WSErrorPayload(code="UNAUTHORIZED", detail="Invalid token").model_dump())
            return

        # --- Ownership + race-condition check ---
        async with AsyncSessionLocal() as db:
            submission = await get_submission(db, job_id)

        if submission is None:
            await _send_json(ws, WSErrorPayload(code="NOT_FOUND", detail="Submission not found").model_dump())
            return

        if submission.user_id != user_id:
            await _send_json(ws, WSErrorPayload(code="FORBIDDEN", detail="Access denied").model_dump())
            return

        # --- Ack ---
        await _send_json(ws, WSAckPayload(job_id=job_id_str).model_dump())

        # --- Already completed? Send result immediately ---
        if submission.status == "completed":
            payload = WSResultPayload(
                job_id=job_id_str,
                status=submission.status,
                verdict=submission.verdict,
                execution_time_ms=submission.execution_time_ms,
                memory_used_mb=float(submission.memory_used_mb) if submission.memory_used_mb else None,
                stdout_snippet=submission.stdout_snippet,
                stderr_snippet=submission.stderr_snippet,
            )
            await _send_json(ws, payload.model_dump())
            return

        # --- Subscribe and wait ---
        channel = f"job_updates:{job_id_str}"
        await pubsub.subscribe(channel)

        async def ping_loop() -> None:
            while True:
                await asyncio.sleep(settings.PING_INTERVAL_SEC)
                await _send_json(ws, WSPingPayload().model_dump())

        ping_task = asyncio.create_task(ping_loop())

        try:
            async def listen() -> dict:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        return json.loads(message["data"])
                return {}

            result_data = await asyncio.wait_for(listen(), timeout=settings.WS_TIMEOUT_SEC)
            if result_data:
                await _send_json(ws, {"type": "result", **result_data})
        except asyncio.TimeoutError:
            pass  # client will recover via GET /submissions/{job_id}
        finally:
            ping_task.cancel()

    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
        active_connections.pop(job_id_str, None)
        try:
            await ws.close(code=1000)
        except Exception:
            pass
