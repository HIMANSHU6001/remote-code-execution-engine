"""WS /ws/{job_id} — real-time result delivery via Redis Pub/Sub."""

from __future__ import annotations
import asyncio
import contextlib
import json
import uuid
import redis
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from auth.dependencies import get_current_user
from config.settings import settings
from db.base import AsyncSessionLocal
from db.queries import get_submission
from shared.enums import SubmissionStatus
from shared.models import WSAckPayload, WSErrorPayload, WSPingPayload, WSResultPayload
from api.agent import agent
from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from redis_client import get_async_redis

router = APIRouter()

# In-process registry — one entry per connected client in this uvicorn worker.
# Not shared across workers; each subscribes to Redis Pub/Sub independently.
active_connections: dict[str, WebSocket] = {}


async def _send_json(ws: WebSocket, payload: dict[str, Any]) -> None:
    await ws.send_text(json.dumps(payload))

@router.websocket("/ws/analyze/{session_id}")
async def ws_analyze(websocket: WebSocket, session_id: str):
    print(f"CONNECTED on /ws/analyze/{session_id}", flush=True)
    await websocket.accept()
    
    redis_client = await get_async_redis()
    pubsub = redis_client.pubsub()

    async def safe_send(payload: dict[str, Any]) -> bool:
        try:
            print(f"Sending payload to WS: {payload}", flush=True)
            await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError) as e:
            print(f"Failed to send WS payload: {e}", flush=True)
            return False

    try:
        # Subscribe to the specific session channel and the fallback empty channel
        print(f"Subscribing to Redis channel: session:{session_id}", flush=True)
        await pubsub.subscribe(f"session:{session_id}")
        print(f"Subscribing to Redis channel: session:", flush=True)
        await pubsub.subscribe("session:")

        # The new architecture only uses this WebSocket to forward Redis commands (like highlights)
        # to the frontend, because Lamatic handles the LLM processing over REST.
        while True:
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        event_data = json.loads(message["data"])
                        print(f"Received Redis message: {event_data}", flush=True)
                        if not await safe_send(event_data):
                            return
            except (asyncio.TimeoutError, redis.exceptions.TimeoutError):
                # Suppress Redis read timeouts if channel is idle
                continue
            except Exception as e:
                # Connection dropped
                print(f"Redis listen error: {e}", flush=True)
                break

    except Exception as e:
        print(f"Error in WS loop: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe()
            await pubsub.close()
        print("WebSocket connection closed and cleaned up", flush=True)

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
    print("CONNECTED on ws/{job_id}", flush=True)
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
            await _send_json(
                ws, WSErrorPayload(code="UNAUTHORIZED", detail="Invalid token").model_dump()
            )
            return

        # --- Ownership + race-condition check ---
        async with AsyncSessionLocal() as db:
            submission = await get_submission(db, job_id)

        if submission is None:
            await _send_json(
                ws, WSErrorPayload(code="NOT_FOUND", detail="Submission not found").model_dump()
            )
            return

        if submission.user_id != user_id:
            await _send_json(
                ws, WSErrorPayload(code="FORBIDDEN", detail="Access denied").model_dump()
            )
            return

        # --- Ack ---
        await _send_json(ws, WSAckPayload(job_id=job_id_str).model_dump())

        # --- Already completed? Send result immediately ---
        if submission.status == SubmissionStatus.COMPLETED:
            payload = WSResultPayload(
                job_id=job_id_str,
                status=submission.status,
                verdict=submission.verdict,
                execution_time_ms=submission.execution_time_ms,
                memory_used_mb=float(submission.memory_used_mb)
                if submission.memory_used_mb
                else None,
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

            async def listen() -> dict[str, Any]:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        if isinstance(data, dict):
                            return {str(key): value for key, value in data.items()}
                        return {}
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
        with contextlib.suppress(Exception):
            await ws.close(code=1000)