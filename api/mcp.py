import json
import sys
import os
import asyncio

sys.path.append(os.getcwd())

import main

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
    # Allow preflight CORS
    if request.method == "OPTIONS":
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

        tool_name = payload.get("tool")
        tool_input = payload.get("input", {})

        if not tool_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing tool name"})
            }

        # Call FastMCP tool
        result = await main.mcp.call_tool(tool_name, tool_input)

        # 🔑 UNWRAP MCP CONTENT: try to extract text or a 'result' key from common return shapes
        def _unwrap(res):
            if hasattr(res, "text"):
                return res.text
            if isinstance(res, dict) and "result" in res:
                return res["result"]
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

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
            "body": json.dumps({"result": output})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
