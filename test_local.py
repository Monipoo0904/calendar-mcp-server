"""
Local Testing Script for Calendar MCP Server

This script provides a simple way to test the Vercel API handler locally
without deploying to Vercel. It simulates an HTTP POST request and calls
the handler function directly.

Purpose:
- Test MCP tools locally before deployment
- Validate tool functionality and responses
- Debug issues without cloud deployment
- Example of how to call the API handler

Usage:
  python test_local.py

Expected Output:
  The script adds a test event and prints the handler response including
  the status code and result/error message.

Test Case:
  Tool: add_event
  Input: {"title": "Demo", "date": "2026-01-01", "description": "Test event"}

Future Testing Enhancements:
- Add comprehensive test suite with pytest
- Test all MCP tools (add, view, delete, summarize)
- Test error cases (invalid dates, missing parameters)
- Test OAuth 2.0 authentication flow (when implemented)
- Test .ics file import/export (when implemented)
"""

import asyncio
from api.mcp import handler


class Req:
    """
    Mock request object that simulates a Vercel HTTP request.
    
    Attributes:
        method: HTTP method (GET, POST, etc.)
        json: Parsed JSON payload from request body
    
    This class mimics the structure of Vercel's request object to allow
    local testing without deploying to the serverless environment.
    """
    method = "POST"
    
    # Sample request payload for testing add_event tool
    json = {
        "tool": "add_event",
        "input": {
            "title": "Demo",
            "date": "2026-01-01",
            "description": "Test event"
        }
    }


async def main():
    """
    Main test function that calls the API handler with mock request.
    
    This async function:
    1. Creates a mock request object
    2. Calls the API handler
    3. Prints the response
    
    To test other tools, modify the Req.json dictionary above.
    """
    response = await handler(Req())
    print(response)


# Execute the async test function
asyncio.run(main())
