from fastapi import APIRouter
from pydantic import BaseModel
import json
from redis_client import get_async_redis

router = APIRouter()

class AnnotateRequest(BaseModel):
    line: int
    message: str
    session_id: str
    hash: str = ""

@router.post("/annotate")
async def annotate_editor(request: AnnotateRequest):
    redis = await get_async_redis()
    
    print(f"RECEIVED ANNOTATE REQUEST: {request.dict()}", flush=True)
    
    # Sanitize session_id in case Lamatic sends the literal template string "{{...}}"
    s_id = request.session_id
    if "{{" in s_id or not s_id.startswith("user_"):
        print(f"Sanitizing invalid session_id: {s_id}", flush=True)
        s_id = ""
        
    payload = {
        "t": "cmd",
        "v": {"line": request.line, "msg": request.message, "h": request.hash}
    }
    
    channel = f"session:{s_id}"
    print(f"Publishing to Redis channel {channel}: {payload}", flush=True)
    
    await redis.publish(channel, json.dumps(payload))
    return {
        "success": True,
        "message": f"Successfully highlighted line {request.line}",
        "session_id": s_id
    }

@router.get("/execution_state")
async def get_execution_state(run_id: str):
    if not run_id or str(run_id).lower() == "none":
        return {"success": False, "state": "No execution data found. The run_id is missing or invalid."}
        
    redis = await get_async_redis()
    raw_json = await redis.get(f"run_details:{run_id}")
    
    if not raw_json:
        return {"success": False, "state": f"No execution data found in Redis for run_id: {run_id}"}
        
    testcases = json.loads(raw_json)
    result = []
    
    for idx, tc in enumerate(testcases, start=1):
        result.append(f"=== TEST CASE {idx} ===\nVerdict: {tc.get('verdict')}\n\nInput:\n{tc.get('input')}\n\nExpected:\n{tc.get('expected')}\n\nActual:\n{tc.get('actual')}\n\nSTDOUT:\n{tc.get('stdout')}\n")
        
    return {
        "success": True,
        "run_id": run_id,
        "state": "\n".join(result)
    }
