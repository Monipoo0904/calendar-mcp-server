import json
import sys
import os
import asyncio
import traceback

sys.path.append(os.getcwd())

import main


def _log(level: str, message: str):
    print(f"[mcp-handler][{level}] {message}", flush=True)

# -----------------------------------------
# Developer notes (api/mcp.py)
# - Vercel-compatible serverless handler for calling MCP tools from the frontend.
# - Handles CORS preflight (OPTIONS) and expects POST requests with JSON bodies of the form:
#     {"tool": "tool_name", "input": { ... }}
# - This handler supports both frameworks that expose `request.json()` as an async coroutine
#   and frameworks that provide `request.json` as a dict-like attribute by checking and
#   awaiting when necessary.
# - The handler calls `main.mcp.call_tool(tool_name, input)` and uses an `_unwrap()` helper
#   to extract readable text from common return shapes (objects with `.text`, dicts with
#   a `result` key, or lists/tuples containing these). It returns JSON: {"result": <text>}.
# - Error handling:
#   - 204 for OPTIONS preflight
#   - 400 for missing tool name
#   - 405 for unsupported methods
#   - 500 for unexpected errors (exception message is included in the response body)
# - Testing: see `test_local.py` which calls `handler()` directly with an async stub.
# - When adding new tools in `main.py`, ensure they return strings or serializable types
#   so the `_unwrap()` helper can extract meaningful output for the frontend.
# -----------------------------------------

async def handler(request):
    _log("INFO", f"Incoming request method={getattr(request, 'method', None)}")

    # Allow preflight CORS
    if request.method == "OPTIONS":
        _log("INFO", "Handled CORS preflight request")
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            },
            "body": ""
        }

    if request.method != "POST":
        _log("WARN", f"Rejected non-POST method={request.method}")
        return {
            "statusCode": 405,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Method not allowed"})
        }

    try:
        # Support both sync dicts and async request.json() methods used by some frameworks
        payload = {}
        if hasattr(request, "json"):
            if callable(request.json):
                _maybe = request.json()
                if asyncio.iscoroutine(_maybe):
                    payload = await _maybe
                else:
                    payload = _maybe
            else:
                payload = request.json or {}

        if not isinstance(payload, dict):
            _log("WARN", f"Request payload is not a dict (type={type(payload).__name__})")
            payload = {}

        tool_name = payload.get("tool")
        tool_input = payload.get("input", {})

        if tool_input is None:
            tool_input = {}
        if not isinstance(tool_input, dict):
            _log("WARN", f"Tool input for {tool_name!r} is not a dict (type={type(tool_input).__name__}); coercing to empty dict")
            tool_input = {}

        _log("INFO", f"Tool call requested: tool={tool_name!r}, input_keys={list(tool_input.keys())}")

        if tool_name == "create_tasks" and "milestones" not in tool_input:
            _log("WARN", "create_tasks called without top-level 'milestones' key; this may fail")

        if not tool_name:
            _log("WARN", "Missing tool name in request payload")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing tool name"})
            }

        # Call FastMCP tool
        result = await main.mcp.call_tool(tool_name, tool_input)
        _log("INFO", f"Tool returned type={type(result).__name__}")

        # 🔑 UNWRAP MCP CONTENT: try to extract text or a 'result' key from common return shapes
        def _unwrap(res):
            if hasattr(res, "text"):
                return res.text
            if isinstance(res, dict) and "result" in res:
                return res["result"]
            if isinstance(res, dict):
                return res
            if isinstance(res, (list, tuple)):
                # search for a text-bearing item or dict with 'result'
                for it in res:
                    if hasattr(it, "text"):
                        return it.text
                    if isinstance(it, dict) and "result" in it:
                        return it["result"]
                return " ".join(str(i) for i in res)
            return str(res)

        output = _unwrap(result)

        if tool_name == "research_and_breakdown":
            plan = output if isinstance(output, dict) else None
            if plan is None:
                _log("WARN", "research_and_breakdown result was not a dict after unwrap")
            else:
                milestones = plan.get("milestones")
                if not isinstance(milestones, list):
                    _log("WARN", "research_and_breakdown result missing list 'milestones'")
                else:
                    _log("INFO", f"research_and_breakdown produced milestones={len(milestones)}")

        _log("INFO", f"Returning success for tool={tool_name!r}, output_type={type(output).__name__}")

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
            "body": json.dumps({"result": output})
        }

    except Exception as e:
        _log("ERROR", f"Unhandled exception: {e}")
        _log("ERROR", traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
