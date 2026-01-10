"""
Vercel API Handler for Calendar MCP Server

This module provides a serverless function handler for deploying the Calendar MCP Server
on Vercel. It exposes the MCP tools as a REST API endpoint that can be called via HTTP POST.

Architecture:
- Receives HTTP POST requests with tool name and input parameters
- Routes requests to the appropriate MCP tool in main.py
- Returns tool results as JSON responses
- Handles errors and provides appropriate HTTP status codes

Request Format:
  POST /api/mcp
  Content-Type: application/json
  Body: {
    "tool": "tool_name",
    "input": {
      "param1": "value1",
      "param2": "value2"
    }
  }

Response Format:
  Success (200):
    {"result": "tool output string"}
  
  Error (400/405/500):
    {"error": "error message"}

Supported HTTP Methods:
- POST: Execute MCP tools
- Other methods return 405 Method Not Allowed

Future Enhancements:
- Add authentication middleware for OAuth 2.0
- Implement rate limiting
- Add request logging and monitoring
- Support for streaming responses
- Webhook endpoints for calendar sync notifications
"""

import json
import sys
import os

# Add current directory to Python path to import main module
sys.path.append(os.getcwd())

import main


async def handler(request):
    """
    Async HTTP request handler for Vercel serverless deployment.
    
    This function is the entry point for all HTTP requests to the API endpoint.
    It validates requests, routes them to appropriate MCP tools, and returns formatted responses.
    
    Args:
        request: Vercel request object with method, json, and other HTTP properties
    
    Returns:
        dict: Response object with statusCode and body
            - statusCode: HTTP status code (200, 400, 405, 500)
            - body: JSON-encoded string containing result or error
    
    Flow:
        1. Validate HTTP method (must be POST)
        2. Parse JSON payload and extract tool name and inputs
        3. Call the MCP tool via main.mcp.call_tool()
        4. Extract text result from MCP response object
        5. Return formatted JSON response
    
    Error Handling:
        - 405: Non-POST requests
        - 400: Missing tool name in payload
        - 500: Tool execution errors or unexpected exceptions
    
    Example Usage:
        curl -X POST https://your-app.vercel.app/api/mcp \
          -H "Content-Type: application/json" \
          -d '{"tool": "add_event", "input": {"title": "Meeting", "date": "2026-01-15"}}'
    
    Future Enhancements:
        - Add OAuth 2.0 token validation
        - Implement request signature verification
        - Add CORS headers for web clients
        - Support batch tool execution
    """
    # Validate HTTP method - only POST is allowed
    if request.method != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Method not allowed"})
        }

    try:
        # Parse JSON payload from request body
        # Use request.json to get parsed JSON or empty dict as fallback
        payload = request.json or {}

        # Extract tool name and input parameters from payload
        tool_name = payload.get("tool")
        tool_input = payload.get("input", {})

        # Validate that tool name was provided
        if not tool_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing tool name"})
            }

        # Execute the MCP tool
        # main.mcp.call_tool() is an async function that invokes the specified tool
        # with the provided input parameters
        result = await main.mcp.call_tool(tool_name, tool_input)

        # Extract text content from MCP result object
        # MCP tools return content objects with a 'text' attribute
        # This unwraps the content to get the actual string result
        if hasattr(result, "text"):
            output = result.text
        else:
            # Fallback for future content types (images, files, etc.)
            output = str(result)

        # Return success response with tool output
        return {
            "statusCode": 200,
            "body": json.dumps({"result": output})
        }

    except Exception as e:
        # Catch all exceptions and return 500 error with details
        # This includes tool not found, invalid parameters, and execution errors
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
