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
  
  def find_date_in_msg(s: str):
    """Try to find a date in the message and return (ISO-date, (start, end)) or (None, None).
    Supports: YYYY-MM-DD, MM/DD[/YYYY], month names (e.g. March 5 2026), 'today', 'tomorrow'.
    """
    s_norm = s
    # today / tomorrow
    for tok in ("today", "tomorrow"):
      idx = s_norm.find(tok)
      if idx != -1:
        return parse_date_token(tok), (idx, idx + len(tok))

    # ISO YYYY-MM-DD
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s_norm)
    if m:
      return m.group(1), m.span(1)

    # MM/DD[/YYYY]
    m = re.search(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", s_norm)
    if m:
      part = m.group(1)
      try:
        parts = part.split('/')
        if len(parts) == 3:
          mo,da,yr = parts
          yr = yr if len(yr) == 4 else ('20' + yr)
        else:
          mo,da = parts
          yr = str(datetime.today().year)
        iso = f"{int(yr):04d}-{int(mo):02d}-{int(da):02d}"
        return iso, m.span(1)
      except Exception:
        pass

    # Month name patterns: March 5 2026, Mar 5, March 5th
    months = {
      'january':1,'jan':1,'february':2,'feb':2,'march':3,'mar':3,'april':4,'apr':4,
      'may':5,'june':6,'jun':6,'july':7,'jul':7,'august':8,'aug':8,'september':9,'sep':9,'sept':9,
      'october':10,'oct':10,'november':11,'nov':11,'december':12,'dec':12
    }
    m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b", s_norm)
    if m:
      mon = m.group(1).lower()
      day = int(m.group(2))
      yr = m.group(3)
      if mon in months:
        year = int(yr) if yr else datetime.today().year
        iso = f"{year:04d}-{months[mon]:02d}-{day:02d}"
        return iso, m.span(0)

    return None, None

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

  # Add (support legacy 'add:' shorthand and more natural conversational phrases)
  if low.startswith("add:") or low.startswith("create:") or low.startswith("schedule:"):
    # legacy shorthand: add:Title|YYYY-MM-DD|Optional description
    parts = msg.split(":", 1)[1].split("|")
    if len(parts) < 2:
      return "Invalid add command. Use: add:Title|YYYY-MM-DD|Optional description or say 'Add Meeting on 2026-01-01'"
    title = parts[0].strip()
    date = parts[1].strip()
    description = parts[2].strip() if len(parts) > 2 else ""
    return add_event(title, date, description)

  # Conversational adds: try to find a date token anywhere and treat text around it as the title/description.
  verb_match = re.match(r'^(?:add|create|schedule)\b\s*(.*)$', msg, re.I)
  if verb_match:
    rest = verb_match.group(1).strip()
    # Look for explicit date inside the rest
    date_iso, span = find_date_in_msg(rest)
    if date_iso and span:
      start, end = span
      # title is the text before the date token
      title = rest[:start].strip()
      # strip common leading words like 'on' or 'for' from title
      title = re.sub(r'\b(on|for)\b\s*$', '', title, flags=re.I).strip()
      # description: look for 'about' or 'with' after the date
      desc = ''
      after = rest[end:].strip()
      mdesc = re.search(r'(?:about|with|desc:|description:)\s*(.*)$', after, re.I)
      if mdesc:
        desc = mdesc.group(1).strip()
      # if no explicit title (e.g., user said 'Add on March 5'), ask for title
      if not title:
        return "Please provide a title for the event, e.g. 'Add Dentist on March 5'."
      return add_event(title, date_iso, desc)

    # If no date found but rest is short like 'meeting tomorrow' handled earlier by find_date_in_msg
    # check words like 'today'/'tomorrow' anywhere
    for tok in ('today', 'tomorrow'):
      if tok in rest.lower():
        date_iso = parse_date_token(tok)
        title = re.sub(r'\b' + tok + r'\b', '', rest, flags=re.I).strip()
        title = re.sub(r'\b(on|for)\b\s*$', '', title, flags=re.I).strip()
        if not title:
          return "Please provide a title for the event, e.g. 'Add Lunch tomorrow'."
        return add_event(title, date_iso, '')

    # No date found: fall back to previous behaviors (help message)
    # We still accept simple 'Add <Title>' but ask for a date.
    if rest and len(rest.split()) <= 6:
      return "I can add that — please include a date (e.g. 'on 2026-03-03', 'tomorrow', or 'March 3')."
    # otherwise fall through to help

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
 

