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

@router.websocket("/ws/analyze")
async def ws_analyze(websocket: WebSocket):
    print("CONNECTED on /ws/analyze", flush=True)
    await websocket.accept()
    
    redis_client = await get_async_redis()
    pubsub = redis_client.pubsub()

    async def safe_send(payload: dict[str, Any]) -> bool:
        try:
            await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            return False

    try:
        while True:
            # 1. Wait for message from frontend
            try:
                init_data = await websocket.receive_json()
            except WebSocketDisconnect:
                print("Client disconnected during receive_json")
                break
            
            s_id = init_data.get("session_id", "unknown")
            
            history = init_data.get("history", [])
            raw_history = init_data.get("history", [])
            code = init_data.get("code", "")
            current_hash = init_data.get("hash", "")
            run_id = init_data.get("run_id")

            print(f"Processing request for session: {s_id}")

            sanitized_history = []
            for i, msg in enumerate(raw_history):
                # If we find an assistant message that attempted to call a tool...
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    # Check if the immediately following message is the tool's response
                    if i + 1 < len(raw_history) and raw_history[i+1].get("role") == "tool":
                        sanitized_history.append(msg)
                    else:
                        # Orphaned tool call detected! The WS dropped before the tool finished.
                        # Drop this message to prevent the OpenAI 400 error.
                        print(f"Dropped orphaned tool call for session {s_id}")
                        continue 
                else:
                    sanitized_history.append(msg)
            # Add line numbers to the code block for accuracy
            numbered_lines = [f"{i+1}: {l}" for i, l in enumerate(code.split('\n'))]
            numbered_code = "\n".join(numbered_lines)

            # Inject the Context Anchor
            history_with_context = [
                {
                    "role": "system", 
                    "content": (
                        f"You are a Coding tutor. The user's current code (with line numbers) is:\n\n```\n{numbered_code}\n```\n\n"
                        f"IMPORTANT CONTEXT for tools:\n"
                        f"- session_id: {s_id}\n"
                        f"- hash: {current_hash}\n"
                        f"- run_id: {run_id if run_id else 'None'}\n\n"
                        "Use these exact values as arguments when calling `emit_editor_annotation` or `fetch_execution_state`.\n"
                        "Note: When using `emit_editor_annotation`, use the 1-indexed line numbers shown in the code block above.\n"
                        "DO NOT include any of these technical values (session_id, hash, run_id, etc.) in your text response to the user."
                    )
                }
            ] + sanitized_history


            # Subscribe to the event bus
            await pubsub.subscribe(f"session:{s_id}")

            async def stream_llm(session_id, h, r_id, history_ctx):
                result = Runner.run_streamed(
                    agent, 
                    history_ctx, 
                    context={"session_id": session_id, "hash": h, "run_id": r_id}
                )
                
                in_speak_block = False
                buffer = ""
                sent_any_text = False

                try:
                    async for event in result.stream_events():
                        # Handle Guardrail Trigger emitted as an event
                        if event.type == "input_guardrail_triggered_event":
                            reason = "Your input was blocked because it isn't a coding-related question."
                            if hasattr(event.data, "output_info") and event.data.output_info:
                                reason = str(event.data.output_info)
                                
                            if not await safe_send({
                                "t": "guardrail",
                                "error": "Input blocked by guardrail",
                                "message": reason,
                            }):
                                return
                            return

                        if event.type == "raw_response_event" and hasattr(event.data, "delta"):
                            delta = event.data.delta
                            if getattr(delta, "tool_calls", None):
                                continue
                            
                            content = delta if isinstance(delta, str) else getattr(delta, "content", None)
                            
                            if content:
                                buffer += content
                                
                                if not in_speak_block:
                                    if "<speak>" in buffer:
                                        in_speak_block = True
                                        parts = buffer.split("<speak>", 1)
                                        buffer = parts[1]
                                    else:
                                        if len(buffer) > 7:
                                            buffer = buffer[-7:]
                                        continue

                                if in_speak_block:
                                    if "</speak>" in buffer:
                                        parts = buffer.split("</speak>", 1)
                                        clean_text = parts[0]
                                        if clean_text:
                                            if not await safe_send({"t": "text", "v": clean_text}):
                                                return
                                            sent_any_text = True
                                        buffer = parts[1]
                                        in_speak_block = False
                                    else:
                                        if len(buffer) > 8:
                                            to_send = buffer[:-8]
                                            if to_send:
                                                if not await safe_send({"t": "text", "v": to_send}):
                                                    return
                                                sent_any_text = True
                                            buffer = buffer[-8:]

                except InputGuardrailTripwireTriggered as e:
                    # (You can remove the timing print from inside here)
                    # Some runner implementations raise an exception when the guardrail trips.
                    reason = "Your input was blocked because it isn't a coding-related question."
                    
                    # Try to get the reasoning from the exception
                    if hasattr(e, "output_info") and e.output_info:
                        reason = str(e.output_info)
                    elif hasattr(e, "data") and hasattr(e.data, "output_info") and e.data.output_info:
                        reason = str(e.data.output_info)
                    
                    if not await safe_send({
                        "t": "guardrail",
                        "error": "Input blocked by guardrail",
                        "message": reason,
                    }):
                        return
                    return

                # Final flush
                if in_speak_block and buffer:
                    if "</speak>" in buffer:
                        buffer = buffer.split("</speak>", 1)[0]
                    if buffer:
                        if not await safe_send({"t": "text", "v": buffer}):
                            return
                        sent_any_text = True

            async def stream_redis_events():
                while True:
                    try:
                        async for message in pubsub.listen():
                            if message["type"] == "message":
                                event_data = json.loads(message["data"])
                                if not await safe_send(event_data):
                                    return
                    except (asyncio.TimeoutError, redis.exceptions.TimeoutError):
                        # Suppress Redis read timeouts if channel is idle, just continue listening
                        continue
                    except Exception:
                        # For connection drops or other errors, exit
                        break

            # Multiplexing this specific interaction
            task_a = asyncio.create_task(stream_llm(s_id, current_hash, run_id, history_with_context))
            task_b = asyncio.create_task(stream_redis_events())
            
            try:
                done, pending = await asyncio.wait({task_a, task_b}, return_when=asyncio.FIRST_COMPLETED)

                for task in done:
                    with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                        task.result()
            finally:
                for task in (task_a, task_b):
                    if not task.done():
                        task.cancel()

                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio.gather(task_a, task_b)

                with contextlib.suppress(Exception):
                    await pubsub.unsubscribe(f"session:{s_id}")
            
            if not await safe_send({"t": "sys", "action": "GENERATION_COMPLETE"}):
                break

    except Exception as e:
        print(f"Error in WS loop: {str(e)}")
        import traceback
        traceback.print_exc()
        with contextlib.suppress(Exception):
            await websocket.send_json({
                "t": "error", 
                "message": "An unexpected server error occurred during analysis."
            })
            await websocket.send_json({"t": "sys", "action": "GENERATION_COMPLETE"})
    finally:
        with contextlib.suppress(Exception):
            await pubsub.close()
        print("WebSocket connection closed and cleaned up")

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