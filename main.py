from mcp.server.fastmcp import FastMCP 
from typing import List, Dict 
from datetime import datetime 
import json
import asyncio

# Create an MCP server 
mcp = FastMCP("EventCalendar") 


# In-memory storage for events 
# Each event is a dict: {"title": str, "date": str, "description": str} 
events: List[Dict] = [] 

# Add an event 
@mcp.tool() 

def add_event(title: str, date: str, description: str = "") -> str: 
  """ 
  Add a new calendar event. 
  Date format: YYYY-MM-DD 
  """ 
  try: 
    # Validate date format 
    datetime.strptime(date, "%Y-%m-%d") 
    events.append({"title": title, "date": date, "description": description}) 
    return f"Event '{title}' added for {date}." 
  except ValueError: 
    return "Invalid date format. Use YYYY-MM-DD." 
# View all events 
@mcp.tool() 

def view_events() -> str: 
  """ 
  Return all events in the calendar. 
  """ 
  if not events: 
    return "No events scheduled." 
  result = "Calendar Events:\n" 
  for event in sorted(events, key=lambda x: x["date"]): 
    desc = f" - {event['description']}" if event['description'] else "" 
    result += f"- {event['date']}: {event['title']}{desc}\n" 
  return result 
# Delete an event by title 
@mcp.tool() 

def delete_event(title: str) -> str: 
  """ 
  Delete an event by its title. 
  """ 
  initial_length = len(events) 
  events[:] = [e for e in events if e["title"].lower() != title.lower()] 
  if len(events) < initial_length: 
    return f"Event '{title}' deleted." 
  else: 
    return f"No event found with title '{title}'." 

# Summarize events 
@mcp.prompt() 
def summarize_events() -> str: 
  """
  Generate a summary of upcoming events. 
  """ 

  if not events: 
    return "No events scheduled." 
  summary = "Upcoming Events Summary:\n" 
  for e in sorted(events, key=lambda x: x["date"]): 
    summary += f"- {e['date']}: {e['title']}" 
    if e['description']: 
      summary += f" ({e['description']})" 
    summary += "\n" 
  return summary 

# Chat-style handler for simple messages/commands
@mcp.tool()
def handle_message(message: str) -> str:
  """
  Simple chat interface for the Event Calendar.

  Supported commands:
  - list -> lists events
  - summarize -> returns the summary
  - add:Title|YYYY-MM-DD|Optional description -> adds event
  - delete:Title -> deletes event by title
  Otherwise returns help text.
  """
  msg = (message or "").strip()
  low = msg.lower()

  if low == "list":
    return view_events()

  if low == "summarize":
    return summarize_events()

  if low.startswith("add:"):
    parts = msg[4:].split("|")
    if len(parts) < 2:
      return "Invalid add command. Use: add:Title|YYYY-MM-DD|Optional description"
    title = parts[0].strip()
    date = parts[1].strip()
    description = parts[2].strip() if len(parts) > 2 else ""
    return add_event(title, date, description)

  if low.startswith("delete:"):
    title = msg[7:].strip()
    return delete_event(title)

  return (
    "Unknown command. Try 'list', 'summarize', "
    "'add:Title|YYYY-MM-DD|desc' or 'delete:Title'."
  )

# Vercel serverless handler
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
        result = await mcp.call_tool(tool_name, tool_input)

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

if __name__ == "__main__": 
  mcp.run() 

