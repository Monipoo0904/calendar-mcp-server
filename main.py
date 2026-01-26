from mcp.server.fastmcp import FastMCP 
from typing import List, Dict 
from datetime import datetime 
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# -----------------------------------------
# Developer notes (main.py)
# - This file defines MCP tools (use @mcp.tool()) and a small FastAPI app that exposes
#   the `/api/mcp` POST endpoint for tool calls. It also mounts the `public/` folder
#   as static files for the frontend. Events are stored in-memory (the `events` list).
# - To add a new tool: add a function decorated with `@mcp.tool()` returning a string
#   or serializable dict. Use `mcp.call_tool()` to invoke tools programmatically.
# -----------------------------------------

import os

# Create an MCP server 
mcp = FastMCP("EventCalendar") 

# Create a FastAPI app for Vercel
app = FastAPI()

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

# Chat-style handler — conversational and flexible
@mcp.tool()
def handle_message(message: str) -> str:
  """
  Conversational chat interface for the Event Calendar.

  Recognizes both terse commands and natural language. Examples:
  - "list" or "list events" -> lists all events
  - "list events on 2026-01-01" or "What's on 2026-01-01?" -> lists events for that date
  - "summarize" / "summary" / "what's coming up" -> summary of upcoming events
  - "add:Title|YYYY-MM-DD|Desc" -> legacy shorthand still supported
  - "Add Birthday on 2026-02-01 about cake" -> conversational add
  - "Create Meeting on 2026-03-03" -> conversational add
  - "Add Meeting tomorrow" -> supports 'today' and 'tomorrow'
  - "delete:Title" or "delete Meeting" or "remove Meeting" -> deletes by title

  If the parser cannot confidently interpret the message, it returns a short help text with examples.
  """
  import re
  from datetime import timedelta

  msg = (message or "").strip()
  low = msg.lower()

  def parse_date_token(s: str):
    s = (s or "").strip().lower()
    if s in ("today",):
      return datetime.today().strftime("%Y-%m-%d")
    if s in ("tomorrow",):
      return (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
      return m.group(1)
    return None

  # Summaries
  if any(k in low for k in ("summarize", "summary", "what's coming", "upcoming", "brief")):
    return summarize_events()

  # Listing events (optionally by date)
  if "list" in low or "events" in low or low.startswith("what"):
    dt = parse_date_token(low)
    if dt:
      filtered = [e for e in events if e["date"] == dt]
      if not filtered:
        return f"No events found for {dt}."
      result = f"Events on {dt}:\n"
      for e in sorted(filtered, key=lambda x: x["date"]):
        desc = f" - {e['description']}" if e['description'] else ""
        result += f"- {e['date']}: {e['title']}{desc}\n"
      return result
    return view_events()

  # Add (support legacy 'add:' and conversational patterns)
  if low.startswith("add:") or low.startswith("create:") or low.startswith("schedule:"):
    parts = msg.split(":", 1)[1].split("|")
    if len(parts) < 2:
      return "Invalid add command. Use: add:Title|YYYY-MM-DD|Optional description or say 'Add Meeting on 2026-01-01'"
    title = parts[0].strip()
    date = parts[1].strip()
    description = parts[2].strip() if len(parts) > 2 else ""
    return add_event(title, date, description)

  m = re.match(r'^(?:add|create|schedule)\s+(?P<title>.+?)\s+(?:on|for)\s+(?P<date>\d{4}-\d{2}-\d{2})(?:\s*(?:about|desc:|description:)\s*(?P<desc>.*))?$', msg, re.I)
  if m:
    title = m.group('title').strip()
    date = m.group('date').strip()
    description = (m.group('desc') or '').strip()
    return add_event(title, date, description)

  # 'Add ... tomorrow' or 'Add ... today'
  m2 = re.match(r'^(?:add|create|schedule)\s+(?P<title>.+?)\s+(?P<d>today|tomorrow)$', msg, re.I)
  if m2:
    title = m2.group('title').strip()
    date = parse_date_token(m2.group('d'))
    if date:
      return add_event(title, date, "")
    return "Couldn't parse the date. Use YYYY-MM-DD, 'today' or 'tomorrow'."

  # Delete (support legacy 'delete:' and conversational forms)
  if low.startswith("delete:"):
    title = msg.split(":", 1)[1].strip()
    return delete_event(title)
  m = re.match(r'^(?:delete|remove|cancel)\s+(?:the\s+)?(?:event\s+)?(?P<title>.+)$', msg, re.I)
  if m:
    title = m.group('title').strip()
    return delete_event(title)

  # Fallback help text
  return (
    "Sorry, I didn't understand. Try conversational commands like:\n"
    "- \"Add Birthday on 2026-02-01\"\n"
    "- \"Create Meeting on 2026-03-03 about planning\"\n"
    "- \"List events on 2026-03-03\" or \"What's on 2026-03-03?\"\n"
    "- \"Summarize upcoming\"\n"
    "You can also use the shorthand: add:Title|YYYY-MM-DD|Desc, delete:Title, list, summarize."
  )

# FastAPI endpoint for MCP tool calls
@app.post("/api/mcp")
async def call_mcp(request: Request):
    try:
        payload = await request.json()
        tool_name = payload.get("tool")
        tool_input = payload.get("input", {})

        if not tool_name:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing tool name"}
            )

        # Call FastMCP tool
        result = await mcp.call_tool(tool_name, tool_input)

        # Unwrap MCP content
        def _unwrap(res):
            if hasattr(res, "text"):
                return res.text
            if isinstance(res, dict) and "result" in res:
                return res["result"]
            if isinstance(res, (list, tuple)):
                for it in res:
                    if hasattr(it, "text"):
                        return it.text
                    if isinstance(it, dict) and "result" in it:
                        return it["result"]
                return " ".join(str(i) for i in res)
            return str(res)

        output = _unwrap(result)
        return JSONResponse(
            status_code=200,
            content={"result": output}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# Serve static files from public directory using an absolute path so Vercel finds them
public_dir = os.path.join(os.path.dirname(__file__), "public")
if os.path.isdir(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")
# Fallback root in case StaticFiles isn't mounted for some reason
from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
async def root_index():
    index_path = os.path.join(os.path.dirname(__file__), "public", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse(status_code=404, content={"detail": "Not Found"})

if __name__ == "__main__": 
  mcp.run()
 

