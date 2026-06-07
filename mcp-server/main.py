import json
import redis.asyncio as redis
from fastmcp import FastMCP
import os
from typing import Optional

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

mcp = FastMCP("RCE_Code_Editor_Assistant_Tools")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

@mcp.tool()
async def emit_editor_annotation(line: int, message: str, hash: str = "", session_id: str = "") -> str:
    """Highlights a line in the user's IDE. Use this to point out bugs."""
    try:
        payload = {
            "t": "cmd",
            "v": {"line": line, "msg": message, "h": hash}
        }
        await redis_client.publish(f"session:{session_id}", json.dumps(payload))
        return f"Successfully highlighted line {line}"
    except Exception as e:
        # Catch all errors and return as a string so the SDK doesn't choke
        return f"Tool execution failed: {str(e)}"


@mcp.tool()
async def fetch_execution_state(run_id: Optional[str] = None) -> str:
    """Fetches the results of the code execution test cases."""
    try:
        # Handle cases where the LLM passes "None", null, or empty string
        if not run_id or str(run_id).lower() == "none":
            return "No execution data found. The run_id is missing or invalid."

        raw_json = await redis_client.get(f"run_details:{run_id}")

        if not raw_json:
            return f"No execution data found in Redis for run_id: {run_id}"

        testcases = json.loads(raw_json)
        result = []

        for idx, tc in enumerate(testcases, start=1):
            result.append(f"""
=== TEST CASE {idx} ===
Verdict: {tc.get("verdict")}

Input:
{tc.get("input")}

Expected:
{tc.get("expected")}

Actual:
{tc.get("actual")}

STDOUT:
{tc.get("stdout")}
""")

        return "\n".join(result)
    except Exception as e:
         return f"Tool execution failed: {str(e)}"


if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8001
    )