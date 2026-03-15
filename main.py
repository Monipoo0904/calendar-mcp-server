from mcp.server.fastmcp import FastMCP 
from typing import List, Dict 
from datetime import datetime 
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, RedirectResponse
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
import json
import httpx
import secrets
from urllib.parse import urlencode
from datetime import datetime, timedelta

# Create an MCP server 
mcp = FastMCP("EventCalendar") 

# Create a FastAPI app for Vercel
app = FastAPI()

# In-memory storage for events 
# Each event is a dict: {"title": str, "date": str, "description": str} 
events: List[Dict] = []

# Student lesson-planning integration notes
# - Data source: the webhook below is expected to return student skill rows.
# - Supported payload shapes:
#   1) top-level list of row objects
#   2) object with one of: rows, data, items, result, records, students
#   3) single row object
# - Expected row columns (case/spacing tolerant):
#   row number, first name, last name, check-in, skill
# - The normalization/index helpers are intentionally tolerant to schema drift
#   because external automations often rename columns with underscores/spaces.
# - The UI uses two response fields from `personalized_lesson_plans`:
#   - available_students: for rendering the student chooser
#   - lesson_plans: lesson sessions used to build calendar milestones
# - If webhook access fails, the tool returns an `error` key rather than
#   raising, so the chat client can show a user-friendly message.
STUDENT_SKILLS_WEBHOOK_URL = os.getenv(
  "STUDENT_SKILLS_WEBHOOK_URL",
  "https://myvillageproject.app.n8n.cloud/webhook/student-skills"
)


def _normalize_skill_row(row: dict) -> dict:
  """Map webhook row variants into a consistent student-skill shape.

  Output fields are stable and used downstream by the student planner:
  - first_name
  - last_name
  - check_in
  - skill
  """
  if not isinstance(row, dict):
    return {}

  # Normalize keys to tolerate variants like "first name", "First_Name", etc.
  keymap = {}
  for k, v in row.items():
    norm = re.sub(r"[^a-z0-9]", "", str(k).lower())
    keymap[norm] = v

  first = str(keymap.get("firstname", "")).strip()
  last = str(keymap.get("lastname", "")).strip()
  check_in = str(keymap.get("checkin", "")).strip()
  skill = str(keymap.get("skill", "")).strip()

  if not first and not last:
    return {}

  return {
    "first_name": first,
    "last_name": last,
    "check_in": check_in,
    "skill": skill,
  }


def _extract_rows_from_webhook_payload(payload):
  """Extract candidate row dicts from common webhook response shapes.

  This function keeps the integration resilient when n8n or upstream sheets
  change the outer envelope of the response.
  """
  if isinstance(payload, list):
    return [r for r in payload if isinstance(r, dict)]

  if not isinstance(payload, dict):
    return []

  for key in ("rows", "data", "items", "result", "records", "students"):
    v = payload.get(key)
    if isinstance(v, list):
      return [r for r in v if isinstance(r, dict)]

  # Some webhooks return a single row object
  return [payload]


def _build_student_strength_index(rows: List[dict]) -> List[dict]:
  """Group normalized rows by student and summarize top strengths.

  Strength ranking is frequency-based: repeated skills are treated as stronger
  indicators and surfaced first.
  """
  grouped: Dict[str, Dict] = {}

  for raw in rows:
    row = _normalize_skill_row(raw)
    if not row:
      continue
    full_name = (f"{row['first_name']} {row['last_name']}").strip()
    if not full_name:
      continue

    if full_name not in grouped:
      grouped[full_name] = {
        "student": full_name,
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "check_ins": [],
        "skills": {},
      }

    if row["check_in"]:
      grouped[full_name]["check_ins"].append(row["check_in"])
    if row["skill"]:
      grouped[full_name]["skills"][row["skill"]] = grouped[full_name]["skills"].get(row["skill"], 0) + 1

  results = []
  for data in grouped.values():
    skills_sorted = sorted(data["skills"].items(), key=lambda x: (-x[1], x[0].lower()))
    top_strengths = [name for name, _ in skills_sorted[:3]]
    results.append({
      "student": data["student"],
      "first_name": data["first_name"],
      "last_name": data["last_name"],
      "last_check_in": data["check_ins"][-1] if data["check_ins"] else "",
      "strengths": top_strengths,
      "skill_counts": data["skills"],
    })

  results.sort(key=lambda s: s["student"].lower())
  return results


def _make_lesson_plan_for_student(student: dict, lesson_goal: str = "") -> dict:
  """Create a lightweight, strengths-based lesson plan for one student.

  The resulting `sessions` array is intentionally compatible with the client
  helper that transforms sessions into calendar milestones.
  """
  name = student.get("student", "Student")
  last_check_in = student.get("last_check_in", "")
  strengths = student.get("strengths") or []
  s1 = strengths[0] if len(strengths) > 0 else "participation"
  s2 = strengths[1] if len(strengths) > 1 else s1
  s3 = strengths[2] if len(strengths) > 2 else s2
  goal_text = lesson_goal.strip() if isinstance(lesson_goal, str) else ""

  lesson_focus = goal_text or f"Build confidence using {s1}"
  student_objective = (
    f"Use {s1} and {s2} to make measurable progress toward: {lesson_focus}"
    if goal_text
    else f"Use {s1} and {s2} to strengthen confidence and independent work habits."
  )
  sessions = [
    {
      "title": "Session 1: Strength-Led Warmup",
      "objective": (
        f"Leverage {s1} as an entry point and set a quick-win task"
        + (f" aligned to {lesson_focus}." if goal_text else ".")
      ),
      "activities": [
        f"5-minute check-in and reflection connected to {s1}.",
        f"Short guided task where {name} demonstrates {s1}.",
        "Exit ticket: one success and one question.",
      ],
    },
    {
      "title": "Session 2: Challenge and Collaboration",
      "objective": (
        f"Combine {s1} with {s2} through a collaborative activity"
        + (f" that advances {lesson_focus}." if goal_text else ".")
      ),
      "activities": [
        f"Partner mini-project that requires {s1} and {s2}.",
        "Teacher conference for feedback and stretch goal.",
        "Peer feedback round using a simple rubric.",
      ],
    },
    {
      "title": "Session 3: Independent Application",
      "objective": (
        f"Apply strengths ({s1}, {s2}, {s3}) to an independent deliverable"
        + (f" connected to {lesson_focus}." if goal_text else ".")
      ),
      "activities": [
        "Independent work block with milestone checkpoints.",
        "Presentation or demo of finished work.",
        "Reflection: next skill to strengthen.",
      ],
    },
  ]

  return {
    "student": name,
    "last_check_in": last_check_in,
    "focus": lesson_focus,
    "student_objective": student_objective,
    "strengths": strengths,
    "sessions": sessions,
  }


def _infer_needed_strength_terms(goal_text: str) -> List[str]:
  """Infer likely needed strengths from project-goal keywords."""
  text = (goal_text or "").lower()
  if not text:
    return []

  keyword_to_strengths = {
    "presentation": ["public speaking", "communication"],
    "pitch": ["public speaking", "communication"],
    "video": ["editing", "storytelling", "creativity"],
    "design": ["design", "creativity"],
    "prototype": ["problem solving", "engineering", "design"],
    "code": ["coding", "programming", "logic"],
    "build": ["problem solving", "collaboration"],
    "research": ["research", "analysis", "writing"],
    "essay": ["writing", "analysis"],
    "campaign": ["communication", "leadership", "design"],
    "event": ["planning", "organization", "leadership"],
    "budget": ["math", "analysis", "organization"],
    "team": ["collaboration", "leadership", "communication"],
    "science": ["analysis", "research", "problem solving"],
    "math": ["math", "logic", "analysis"],
    "robot": ["engineering", "coding", "problem solving"],
  }

  inferred = []
  for keyword, strengths in keyword_to_strengths.items():
    if keyword in text:
      inferred.extend(strengths)

  # Keep insertion order while de-duping.
  deduped = []
  seen = set()
  for item in inferred:
    if item not in seen:
      seen.add(item)
      deduped.append(item)
  return deduped


def _normalize_skill_terms(skill_counts: dict) -> List[str]:
  """Normalize skill labels for lightweight term matching."""
  if not isinstance(skill_counts, dict):
    return []
  terms = []
  for skill in skill_counts.keys():
    s = str(skill or "").strip().lower()
    if s:
      terms.append(s)
  return terms


def _compute_additional_student_recommendations(
  students_index: List[dict],
  selected_students: List[dict],
  goal_text: str,
  deadline: str = "",
) -> List[dict]:
  """Suggest students who cover strengths not currently represented by selection."""
  needed_terms = _infer_needed_strength_terms(goal_text)
  if not needed_terms:
    return []

  selected_names = {s.get("student", "") for s in selected_students}
  covered = set()
  for s in selected_students:
    for term in _normalize_skill_terms(s.get("skill_counts", {})):
      for needed in needed_terms:
        if needed in term or term in needed:
          covered.add(needed)

  missing_terms = [t for t in needed_terms if t not in covered]
  if not missing_terms:
    return []

  # If deadline is close, keep fewer but stronger recommendations.
  deadline_days = None
  if isinstance(deadline, str) and deadline.strip():
    try:
      deadline_days = (datetime.strptime(deadline.strip(), "%Y-%m-%d") - datetime.now()).days
    except Exception:
      deadline_days = None

  candidates = []
  for candidate in students_index:
    name = candidate.get("student", "")
    if not name or name in selected_names:
      continue

    matched = []
    skill_terms = _normalize_skill_terms(candidate.get("skill_counts", {}))
    for needed in missing_terms:
      if any((needed in skill) or (skill in needed) for skill in skill_terms):
        matched.append(needed)

    if not matched:
      continue

    score = len(set(matched))
    candidates.append({
      "student": name,
      "matched_strengths": sorted(set(matched)),
      "score": score,
      "reason": f"Can add: {', '.join(sorted(set(matched)))}",
    })

  candidates.sort(key=lambda c: (-c["score"], c["student"].lower()))
  limit = 2 if deadline_days is not None and deadline_days <= 14 else 4
  return candidates[:limit]


@mcp.tool()
def personalized_lesson_plans(students: str = "", lesson_goal: str = "", max_students: int = 10, deadline: str = "") -> dict:
  """Build personalized lesson plans from webhook student skill rows.

  Arguments:
  - students: comma-separated names or partial names. Empty means all students.
  - lesson_goal: optional focus string applied to each generated plan.
  - max_students: cap for response size; bounded server-side for safety.

  Returns:
  - available_students: full directory for UI selection.
  - selected_students: names matched by the students filter.
  - lesson_plans: per-student strengths-based sessions.
  - summary: human-readable text for direct chat display.
  """
  try:
    max_n = max(1, min(int(max_students), 50))
  except Exception:
    max_n = 10

  try:
    resp = httpx.get(STUDENT_SKILLS_WEBHOOK_URL, timeout=15.0)
    if resp.status_code != 200:
      return {
        "error": f"Failed to fetch student skills (status {resp.status_code}).",
        "webhook_url": STUDENT_SKILLS_WEBHOOK_URL,
      }
    payload = resp.json()
  except Exception as e:
    return {
      "error": f"Unable to fetch student skills: {e}",
      "webhook_url": STUDENT_SKILLS_WEBHOOK_URL,
    }

  rows = _extract_rows_from_webhook_payload(payload)
  students_index = _build_student_strength_index(rows)
  if not students_index:
    return {
      "error": "No valid student rows were found in the webhook response.",
      "webhook_url": STUDENT_SKILLS_WEBHOOK_URL,
    }

  # Optional name filtering from comma-separated input, e.g. "Ava Smith, Noah"
  requested_names = []
  if isinstance(students, str) and students.strip():
    requested_names = [n.strip().lower() for n in students.split(",") if n.strip()]

  filtered = students_index
  if requested_names:
    filtered = [
      s for s in students_index
      if any(name in s["student"].lower() for name in requested_names)
    ]

  selected = filtered[:max_n]
  lesson_plans = [_make_lesson_plan_for_student(s, lesson_goal=lesson_goal) for s in selected]
  available_students = [s.get("student", "") for s in students_index if s.get("student")]
  selected_students = [s.get("student", "") for s in selected if s.get("student")]
  recommended_additional_students = _compute_additional_student_recommendations(
    students_index=students_index,
    selected_students=selected,
    goal_text=lesson_goal,
    deadline=deadline,
  )

  summary_lines = [
    f"Personalized lesson plans generated for {len(lesson_plans)} student(s).",
    f"Source: {STUDENT_SKILLS_WEBHOOK_URL}",
  ]
  for plan in lesson_plans:
    strengths = ", ".join(plan.get("strengths") or ["(no skills reported)"])
    summary_lines.append("")
    summary_lines.append(f"{plan['student']} | strengths: {strengths}")
    for idx, sess in enumerate(plan.get("sessions", []), start=1):
      summary_lines.append(f"  {idx}. {sess['title']} - {sess['objective']}")

  if recommended_additional_students:
    summary_lines.append("")
    summary_lines.append("Suggested additional students for missing strengths:")
    for r in recommended_additional_students:
      summary_lines.append(f"- {r['student']} ({', '.join(r['matched_strengths'])})")

  return {
    "webhook_url": STUDENT_SKILLS_WEBHOOK_URL,
    "requested_students": students,
    "lesson_goal": lesson_goal,
    "available_students": available_students,
    "selected_students": selected_students,
    "recommended_additional_students": recommended_additional_students,
    "deadline": deadline,
    "count": len(lesson_plans),
    "lesson_plans": lesson_plans,
    "summary": "\n".join(summary_lines),
  }

# Add an event 
@mcp.tool() 

def add_event(title: str, date: str, description: str = "", end: str = None) -> str: 
  """ 
  Add a new calendar event. 
  Date format: YYYY-MM-DD 
  """ 
  try: 
    # Accept date with optional time. Supported input formats:
    #  - YYYY-MM-DD
    #  - YYYY-MM-DD HH:MM
    #  - YYYY-MM-DDTHH:MM
    dt = None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
      try:
        dt = datetime.strptime(date, fmt)
        break
      except Exception:
        dt = None

    if not dt:
      raise ValueError("Invalid date format")

    # If time component was provided, normalize storage to ISO 8601 without seconds
    if 'T' in date or ' ' in date:
      stored = dt.strftime("%Y-%m-%dT%H:%M")
    else:
      stored = dt.strftime("%Y-%m-%d")

    ev = {"title": title, "date": stored, "description": description}
    # normalize and attach end time if provided (expect same date or full ISO)
    if end:
      try:
        # accept end as 'HH:MM' or full 'YYYY-MM-DDTHH:MM'
        if 'T' in end or ' ' in end or '-' in end:
          # if it's full ISO with date
          edt = None
          for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
              edt = datetime.strptime(end, fmt)
              break
            except Exception:
              edt = None
          if edt:
            ev['end'] = edt.strftime("%Y-%m-%dT%H:%M")
        else:
          # assume time-only 'HH:MM' on same date
          # combine stored date (date part) with end time
          date_part = stored.split('T', 1)[0]
          ev['end'] = f"{date_part}T{end}"
      except Exception:
        # ignore malformed end
        pass

    events.append(ev)
    if ev.get('end'):
      return f"Event '{title}' added for {stored} until {ev.get('end')}."
    return f"Event '{title}' added for {stored}." 
  except ValueError: 
    return "Invalid date format. Use YYYY-MM-DD or include time like 'YYYY-MM-DD 14:30'." 
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
    # Try datetime with time: YYYY-MM-DDTHH:MM or YYYY-MM-DD HH:MM
    m2 = re.search(r"(\d{4}-\d{2}-\d{2})[T ](\d{1,2}:\d{2})", s)
    if m2:
      date_part = m2.group(1)
      time_part = m2.group(2)
      # normalize to YYYY-MM-DDTHH:MM
      return f"{date_part}T{time_part}"
    return None
  
  def find_date_in_msg(s: str):
    """Try to find a date in the message and return (ISO-date, (start, end), end_iso) or (None, None, None).

    Notes for maintainers:
    - This function returns three values: the detected start (ISO date or ISO datetime),
      the character-span tuple for where the date was found, and an optional `end_iso`
      value when the user included a time range (e.g. "3pm-5pm" or "from 3pm to 5pm").
    - `end_iso` is returned as a full ISO datetime string in the form `YYYY-MM-DDTHH:MM`.

    Supported inputs: YYYY-MM-DD, MM/DD[/YYYY], month names (e.g. March 5 2026), 'today',
    'tomorrow', and simple time ranges like '3pm-5pm', 'from 3pm to 5pm', or '3:00-4:30'.
    """
    s_norm = s
    # today / tomorrow
    for tok in ("today", "tomorrow"):
      idx = s_norm.find(tok)
      if idx != -1:
        return parse_date_token(tok), (idx, idx + len(tok)), None

    # ISO YYYY-MM-DD or datetime (YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM)
    m = re.search(r"(\d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2})?)", s_norm)
    if m:
      candidate = m.group(1)
      span = m.span(1)
      # If the ISO capture includes a time, normalize as-is; otherwise try to find a time-range nearby
      # Look for a time-range anywhere in the message (e.g., 'from 3pm to 5pm', '3-5pm')
      range_match = re.search(r"(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)\s*(?:-|to|until|through|–)\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)", s_norm, re.I)
      if range_match:
        start_raw = range_match.group(1)
        end_raw = range_match.group(2)
        start_tt = parse_time_token(start_raw)
        end_tt = parse_time_token(end_raw)
        if start_tt and end_tt:
          # if candidate already has time, honor as start; otherwise combine date with start_tt
          if 'T' in candidate:
            start_iso = candidate
          else:
            start_iso = f"{candidate}T{start_tt}"
          end_iso = f"{candidate.split('T',1)[0]}T{end_tt}"
          return start_iso, span, end_iso
      return candidate, span, None

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
        # Check for a time immediately following (e.g., 'March 5 at 3pm' or 'March 5 15:30')
        after_span_start = m.span(0)[1]
        after = s_norm[after_span_start:after_span_start+80]
        # First try to find a range after the date (e.g., 'at 3pm to 5pm')
        r = re.search(r"(?:at\s*)?(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)\s*(?:-|to|until|through|–)\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)", after, re.I)
        if r:
          start_raw = r.group(1)
          end_raw = r.group(2)
          start_tt = parse_time_token(start_raw)
          end_tt = parse_time_token(end_raw)
          if start_tt and end_tt:
            return f"{iso}T{start_tt}", m.span(0), f"{iso}T{end_tt}"
        # Otherwise try a single time after the date
        tmatch = re.search(r"(?:at\s*)?(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)", after)
        if tmatch:
          traw = tmatch.group(1)
          tt = parse_time_token(traw)
          if tt:
            return f"{iso}T{tt}", m.span(0), None
        # As a last attempt, check the whole message for a general time-range and apply it to this date
        range_match = re.search(r"(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)\s*(?:-|to|until|through|–)\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)", s_norm, re.I)
        if range_match:
          start_raw = range_match.group(1)
          end_raw = range_match.group(2)
          start_tt = parse_time_token(start_raw)
          end_tt = parse_time_token(end_raw)
          if start_tt and end_tt:
            return f"{iso}T{start_tt}", m.span(0), f"{iso}T{end_tt}"
        return iso, m.span(0), None

    return None, None

  def parse_time_token(s: str):
    """Normalize a time token like '3pm', '3:30 pm', or '15:30' to HH:MM (24h)."""
    s = (s or '').strip().lower()
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", s)
    if not m:
      return None
    h = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    ampm = m.group(3)
    if ampm:
      if ampm == 'pm' and h < 12:
        h += 12
      if ampm == 'am' and h == 12:
        h = 0
    return f"{h:02d}:{minute:02d}"

  def normalize_deadline(text: str):
    """Accept YYYY-MM-DD, 'today/tomorrow', or month-name dates."""
    # Try explicit date tokens first
    dt = parse_date_token(text)
    if dt:
      return dt.split("T", 1)[0]
    # Try month-name or embedded date
    d, _, _ = find_date_in_msg(text)
    if d:
      return d.split("T", 1)[0]
    # Try YYYY-MM-DD anywhere
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
      return m.group(1)
    return None

  def normalize_cadence(text: str):
    t = (text or "").lower()
    if "every other day" in t:
      return "every_other_day"
    if "every two weeks" in t or "biweekly" in t:
      return "biweekly"
    if "weekdays" in t or "workdays" in t:
      return "weekdays"
    if "weekly" in t:
      return "weekly"
    if "monthly" in t:
      return "monthly"
    if "daily" in t or "every day" in t:
      return "daily"
    if "custom" in t:
      return "custom"
    return None

  def format_plan(plan: dict, cadence_choice: str = None) -> str:
    if not isinstance(plan, dict):
      return str(plan)
    lines = []
    lines.append(f'Plan for "{plan.get("goal","(goal)")}" (deadline: {plan.get("deadline") or "not specified"}):')
    for i, m in enumerate(plan.get("milestones", []), start=1):
      lines.append(f'{i}. {m.get("title","Milestone")} — due {m.get("due","")}')
      steps = m.get("steps") or []
      if isinstance(steps, list) and steps:
        for step in steps:
          if isinstance(step, str) and step.strip():
            lines.append(f"   - {step.strip()}")
    if plan.get("cadence_suggestions"):
      lines.append("Suggested cadences: " + ", ".join(plan["cadence_suggestions"]))
    if cadence_choice:
      lines.append("Chosen cadence: " + cadence_choice.replace("_", " "))
    return "\n".join(lines)

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

  verb_match = re.match(r'^(?:add|create|schedule)\b\s*(.*)$', msg, re.I)
  if verb_match:
    rest = verb_match.group(1).strip()
    # Look for explicit date inside the rest (may return an end time)
    date_iso, span, end_iso = find_date_in_msg(rest)
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
      return add_event(title, date_iso, desc, end=end_iso)

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

  # For project planning, guide users to use the client-side flow or call research_and_breakdown tool directly
  planning_keywords = (
    "plan", "project", "goal", "accomplish", "breakdown",
    "build", "develop", "launch", "ship", "roadmap", "milestone"
  )
  student_plan_keywords = (
    "lesson plan", "lesson plans", "student plan", "student plans",
    "student skills", "students", "strengths", "personalized lesson"
  )
  if any(k in low for k in student_plan_keywords):
    names = ""
    # Optional pattern: "for Alice Smith, Bob Lee"
    m_names = re.search(r"\bfor\s+(.+)$", msg, re.I)
    if m_names:
      names = m_names.group(1).strip()
      # Remove obvious trailing punctuation.
      names = re.sub(r"[\.!?]+$", "", names)

    plan_data = personalized_lesson_plans(students=names)
    if isinstance(plan_data, dict):
      if plan_data.get("summary"):
        return plan_data["summary"]
      if plan_data.get("error"):
        return f"Could not generate personalized lesson plans: {plan_data['error']}"
    return str(plan_data)

  if any(k in low for k in planning_keywords):
    return "What would you like to accomplish? (Describe your goal and I'll help you plan it out.)"

  # Fallback help text (should rarely hit)
  return (
    "Sorry, I didn't understand. Try commands like:\n"
    "- \"Add Birthday on 2026-02-01\"\n"
    "- \"List events\" or \"List events on 2026-03-03\"\n"
    "- \"Summarize upcoming\"\n"
    "- \"Delete Birthday\"\n"
    "- \"Plan\" to start project planning\n"
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
            if isinstance(res, dict):
                # If it's already a plain dict (like from research_and_breakdown), return as-is
                return res
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


# Outlook/Microsoft OAuth start endpoint
# - Called by the top "Connect to Microsoft Calendar" button in public/script.js.
# - Builds a Microsoft authorize URL using env configuration.
# - Required env var: MS_CLIENT_ID (or MICROSOFT_CLIENT_ID).
# - Optional env vars:
#   - MS_TENANT_ID (default: common)
#   - MS_REDIRECT_URI (default: <base>/redirect_microsoft.html)
#   - MS_SCOPES (default: offline_access User.Read Calendars.ReadWrite)
# - On success, Microsoft redirects to /api/oauth/microsoft/callback which exchanges
#   the code and fetches profile name from Microsoft Graph.
@app.get("/api/oauth/microsoft/start", include_in_schema=False)
async def oauth_microsoft_start(request: Request):
  client_id = os.getenv("MS_CLIENT_ID") or os.getenv("MICROSOFT_CLIENT_ID")
  if not client_id:
    return JSONResponse(
      status_code=501,
      content={
        "error": "Microsoft OAuth is not configured. Set MS_CLIENT_ID in environment variables.",
        "setup": {
          "required": ["MS_CLIENT_ID"],
          "optional": ["MS_TENANT_ID", "MS_REDIRECT_URI", "MS_SCOPES"],
        },
      },
    )

  tenant_id = os.getenv("MS_TENANT_ID", "common").strip() or "common"
  scope = os.getenv("MS_SCOPES", "offline_access User.Read Calendars.ReadWrite")
  redirect_uri = os.getenv("MS_REDIRECT_URI", "").strip()
  if not redirect_uri:
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/api/oauth/microsoft/callback"

  state = secrets.token_urlsafe(24)
  params = {
    "client_id": client_id,
    "response_type": "code",
    "redirect_uri": redirect_uri,
    "response_mode": "query",
    "scope": scope,
    "state": state,
  }
  auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"
  return JSONResponse(status_code=200, content={"auth_url": auth_url})


# Microsoft OAuth callback
# - Exchanges auth code for token, then queries Graph /me for display name.
# - Redirects user back to app with query params consumed by public/script.js:
#   - ms_name: display name for header UI
#   - ms_provider: provider marker (microsoft)
#   - ms_error: present if callback/token/profile lookup failed
@app.get("/api/oauth/microsoft/callback", include_in_schema=False)
async def oauth_microsoft_callback(request: Request):
  base = str(request.base_url).rstrip("/")
  app_redirect = f"{base}/index.html"

  err = request.query_params.get("error", "")
  if err:
    return RedirectResponse(url=f"{app_redirect}?ms_error={err}&ms_provider=microsoft", status_code=302)

  code = request.query_params.get("code", "")
  if not code:
    return RedirectResponse(url=f"{app_redirect}?ms_error=missing_code&ms_provider=microsoft", status_code=302)

  client_id = os.getenv("MS_CLIENT_ID") or os.getenv("MICROSOFT_CLIENT_ID")
  client_secret = os.getenv("MS_CLIENT_SECRET", "")
  tenant_id = os.getenv("MS_TENANT_ID", "common").strip() or "common"
  scope = os.getenv("MS_SCOPES", "offline_access User.Read Calendars.ReadWrite")
  redirect_uri = os.getenv("MS_REDIRECT_URI", "").strip() or f"{base}/api/oauth/microsoft/callback"

  if not client_id or not client_secret:
    return RedirectResponse(url=f"{app_redirect}?ms_error=missing_ms_client_config&ms_provider=microsoft", status_code=302)

  token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
  token_data = {
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": redirect_uri,
    "scope": scope,
  }

  try:
    token_resp = httpx.post(token_url, data=token_data, timeout=20.0)
    if token_resp.status_code != 200:
      return RedirectResponse(url=f"{app_redirect}?ms_error=token_exchange_failed&ms_provider=microsoft", status_code=302)
    token_json = token_resp.json()
    access_token = token_json.get("access_token", "")
    if not access_token:
      return RedirectResponse(url=f"{app_redirect}?ms_error=missing_access_token&ms_provider=microsoft", status_code=302)

    me_resp = httpx.get(
      "https://graph.microsoft.com/v1.0/me?$select=displayName,givenName,mail,userPrincipalName",
      headers={"Authorization": f"Bearer {access_token}"},
      timeout=20.0,
    )
    if me_resp.status_code != 200:
      return RedirectResponse(url=f"{app_redirect}?ms_error=profile_fetch_failed&ms_provider=microsoft", status_code=302)

    profile = me_resp.json()
    display_name = (
      profile.get("displayName")
      or profile.get("givenName")
      or profile.get("mail")
      or profile.get("userPrincipalName")
      or "Microsoft User"
    )
    qs = urlencode({"ms_name": display_name, "ms_provider": "microsoft", "ms_connected": "1"})
    return RedirectResponse(url=f"{app_redirect}?{qs}", status_code=302)
  except Exception:
    return RedirectResponse(url=f"{app_redirect}?ms_error=oauth_callback_exception&ms_provider=microsoft", status_code=302)


@app.get("/export.ics", include_in_schema=False)
async def export_ics(request: Request):
  """Generate a simple iCalendar (.ics) file from in-memory `events`.

  The exporter supports both date-only and timed events. If an event contains a
  time component (stored as `YYYY-MM-DDTHH:MM`) it is emitted as a timed
  `DTSTART` value. If the event also includes an `end` value (a stored
  `YYYY-MM-DDTHH:MM`), the exporter will emit a corresponding `DTEND` field.

  Note: all-day events are exported with `DTSTART;VALUE=DATE`. If you add
  timezone handling later, update this exporter to include `TZID` or convert
  timestamps to UTC.
  """
  import uuid
  import datetime as _dt

  requested_student = request.query_params.get("student", "").strip()
  requested_students_csv = request.query_params.get("students", "").strip()
  requested_students = [
    part.strip().lower()
    for part in requested_students_csv.split(",")
    if part and part.strip()
  ]
  scoped_events = events
  if requested_students:
    requested_set = set(requested_students)
    scoped_events = [
      e for e in events
      if str(e.get("student", "")).strip().lower() in requested_set
    ]
  elif requested_student:
    scoped_events = [
      e for e in events
      if str(e.get("student", "")).strip().lower() == requested_student.lower()
    ]

  lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Event Calendar MCP//EN",
  ]

  now = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
  for e in sorted(scoped_events, key=lambda x: x["date"]):
    uid = str(uuid.uuid4())
    # date in format YYYYMMDD for all-day DTSTART
    desc = e.get('description', '') or ''
    title = e.get('title', '')
    if e.get('milestone'):
      title = f"[Milestone] {title}" if title else "[Milestone]"
    if 'T' in e.get('date', ''):
      # timed event: YYYY-MM-DDTHH:MM
      try:
        d = _dt.datetime.strptime(e['date'], '%Y-%m-%dT%H:%M')
        dtstr = d.strftime('%Y%m%dT%H%M%S')
        vevent = [
          "BEGIN:VEVENT",
          f"UID:{uid}",
          f"DTSTAMP:{now}",
          f"DTSTART:{dtstr}",
        ]
        # If an end time exists, emit DTEND
        if e.get('end'):
          try:
            ed = _dt.datetime.strptime(e['end'], '%Y-%m-%dT%H:%M')
            dtend = ed.strftime('%Y%m%dT%H%M%S')
            vevent.append(f"DTEND:{dtend}")
          except Exception:
            pass
        vevent.extend([
          f"SUMMARY:{title}",
          f"DESCRIPTION:{desc}",
          "END:VEVENT",
        ])
        lines.extend(vevent)
      except Exception:
        # fallback to all-day
        dtstart = e['date'].split('T',1)[0].replace('-', '')
        vevent = [
          "BEGIN:VEVENT",
          f"UID:{uid}",
          f"DTSTAMP:{now}",
          f"DTSTART;VALUE=DATE:{dtstart}",
        ]
        # If an end (all-day) exists and is a date, emit DTEND;VALUE=DATE
        if e.get('end'):
          try:
            ed = _dt.datetime.strptime(e['end'].split('T',1)[0], '%Y-%m-%d')
            dtend_date = (ed + _dt.timedelta(days=1)).strftime('%Y%m%d')
            vevent.append(f"DTEND;VALUE=DATE:{dtend_date}")
          except Exception:
            pass
        vevent.extend([
          f"SUMMARY:{title}",
          f"DESCRIPTION:{desc}",
          "END:VEVENT",
        ])
        lines.extend(vevent)
    else:
      dtstart = e["date"].replace('-', '')
      lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{desc}",
        "END:VEVENT",
      ])

  lines.append("END:VCALENDAR")
  content = "\r\n".join(lines) + "\r\n"

  if requested_students:
    filename = "selected_students_events.ics"
  elif requested_student:
    safe_student = re.sub(r"[^a-zA-Z0-9_-]", "_", requested_student)[:40] or "student"
    filename = f"{safe_student}_events.ics"
  else:
    filename = "events.ics"
  headers = {"Content-Disposition": f"attachment; filename={filename}"}
  return Response(content=content, media_type="text/calendar; charset=utf-8", headers=headers)


@app.get("/export-single.ics", include_in_schema=False)
async def export_single_ics(request: Request):
  """Export a single event/milestone as its own ICS file, looked up by title (case-insensitive)."""
  import uuid
  import datetime as _dt

  title_param = request.query_params.get("title", "").strip()
  if not title_param:
    return JSONResponse(status_code=400, content={"detail": "title query parameter required"})

  ev = next((e for e in events if e.get("title", "").lower() == title_param.lower()), None)
  if not ev:
    return JSONResponse(status_code=404, content={"detail": "Event not found"})

  uid = str(uuid.uuid4())
  now = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
  desc = ev.get("description", "") or ""
  title = ev.get("title", "")
  if ev.get("milestone"):
    title = f"[Milestone] {title}" if title else "[Milestone]"

  lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Event Calendar MCP//EN",
  ]

  if "T" in ev.get("date", ""):
    try:
      d = _dt.datetime.strptime(ev["date"], "%Y-%m-%dT%H:%M")
      dtstr = d.strftime("%Y%m%dT%H%M%S")
      vevent = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{dtstr}",
      ]
      if ev.get("end"):
        try:
          ed = _dt.datetime.strptime(ev["end"], "%Y-%m-%dT%H:%M")
          vevent.append(f"DTEND:{ed.strftime('%Y%m%dT%H%M%S')}")
        except Exception:
          pass
      vevent.extend([f"SUMMARY:{title}", f"DESCRIPTION:{desc}", "END:VEVENT"])
      lines.extend(vevent)
    except Exception:
      dtstart = ev["date"].split("T", 1)[0].replace("-", "")
      lines.extend([
        "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}",
        f"DTSTART;VALUE=DATE:{dtstart}", f"SUMMARY:{title}",
        f"DESCRIPTION:{desc}", "END:VEVENT",
      ])
  else:
    dtstart = ev["date"].replace("-", "")
    lines.extend([
      "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}",
      f"DTSTART;VALUE=DATE:{dtstart}", f"SUMMARY:{title}",
      f"DESCRIPTION:{desc}", "END:VEVENT",
    ])

  lines.append("END:VCALENDAR")
  content = "\r\n".join(lines) + "\r\n"
  safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:40]
  headers = {"Content-Disposition": f"attachment; filename={safe_title}.ics"}
  return Response(content=content, media_type="text/calendar; charset=utf-8", headers=headers)


if __name__ == "__main__":
  mcp.run()

@mcp.tool()
def set_recurrence(title: str, frequency: str = "none", interval: int = 1) -> str:
    """
    Set recurrence for the most recent event with `title`.

    frequency values supported:
      - none: remove recurrence
      - daily: every day
      - every_other_day: every 2 days
      - weekly: every week
      - biweekly: every 2 weeks
      - weekdays: Mon-Fri each week day
      - workdays: alias for weekdays
      - monthly: once each month on same day (or user-provided day)
      - monthly_on_day: monthly on a specific day (use `interval` to supply day number)
      - custom: treated as daily with given interval (simple fallback)

    interval meaning:
      - for daily/weekly/biweekly/etc: interval number (e.g. 2 = every 2 weeks)
      - for monthly_on_day: integer day of month (1-31)
      - for custom: numeric step used as days

    This function sets `recurrence_rrule` (simple RFC-like string) and a basic
    `next_due` computed by stepping the original event date forward until it's in the future.
    Note: this is a simple stepping algorithm; for full RFC5545 semantics use an rrule library.
    """
    from datetime import datetime, timedelta

    # find most recent event matching title (case-insensitive)
    candidates = [e for e in events if e.get("title", "").lower() == title.lower()]
    if not candidates:
        return f"No event found with title '{title}' to set recurrence."
    ev = candidates[-1]  # pick most recently added match

    # Normalized frequency keys and simple RRULE-like representation
    freq_map = {
        "none": None,
        "daily": "FREQ=DAILY;INTERVAL=1",
        "every_other_day": "FREQ=DAILY;INTERVAL=2",
        "weekly": "FREQ=WEEKLY;INTERVAL=1",
        "biweekly": "FREQ=WEEKLY;INTERVAL=2",
        "weekdays": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        "workdays": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        "monthly": "FREQ=MONTHLY;INTERVAL=1",
        # monthly_on_day will be composed below when interval includes day-of-month
    }

    # Build rrule depending on requested frequency
    rrule = None
    key = frequency.lower()
    if key in freq_map:
        rrule = freq_map[key]
    elif key == "monthly_on_day":
        day = int(interval) if interval and 1 <= int(interval) <= 31 else None
        if day:
            rrule = f"FREQ=MONTHLY;BYMONTHDAY={day};INTERVAL=1"
        else:
            return "Invalid day-of-month for monthly_on_day. Provide interval as day number (1-31)."
    elif key == "custom":
        # fallback: allow custom interval in days
        if interval and int(interval) > 0:
            rrule = f"FREQ=DAILY;INTERVAL={int(interval)}"
        else:
            return "Invalid custom interval; must be a positive integer."
    else:
        return f"Unsupported recurrence frequency '{frequency}'."

    # Persist recurrence metadata
    ev["recurrence_rrule"] = rrule
    ev["recur_freq"] = frequency if rrule else None
    ev["recur_interval"] = int(interval) if rrule and isinstance(interval, (int, str)) and str(interval).isdigit() else None

    # Compute a simple next_due: step forward from the event's date until > now
    # This is intentionally simple; production should use an rrule library.
    try:
        start = ev.get("date") or ev.get("start") or ev.get("datetime") or ev.get("next_due")
        if not start:
            ev["next_due"] = None
            return f"Recurrence set for '{title}', but event has no base date to compute next occurrence."

        # normalize date/datetime parsing (support YYYY-MM-DD and YYYY-MM-DDTHH:MM)
        if "T" in start:
            cur = datetime.strptime(start, "%Y-%m-%dT%H:%M")
            use_time = True
        else:
            cur = datetime.strptime(start, "%Y-%m-%d")
            use_time = False

        now = datetime.now()
        # choose stepping rules from rrule string
        if not rrule:
            ev["next_due"] = cur.strftime("%Y-%m-%dT%H:%M") if use_time else cur.strftime("%Y-%m-%d")
            return f"Recurrence for '{title}' set to none."

        # interpret simplest cases
        if "FREQ=DAILY" in rrule:
            interval_days = 1
            # extract INTERVAL if present
            if "INTERVAL=" in rrule:
                try:
                    interval_days = int(rrule.split("INTERVAL=")[1].split(";")[0])
                except Exception:
                    interval_days = 1
            step = timedelta(days=interval_days)
        elif "FREQ=WEEKLY" in rrule:
            # for BYDAY weekly patterns we step by 1 day until we match allowed weekdays
            if "BYDAY=" in rrule:
                allowed = rrule.split("BYDAY=")[1].split(";")[0].split(",")
                # map weekday names to integers Mon=0..Sun=6
                wkmap = {"MO":0,"TU":1,"WE":2,"TH":3,"FR":4,"SA":5,"SU":6}
                allowed_idx = [wkmap[d] for d in allowed if d in wkmap]
                # advance day-by-day until allowed weekday in future
                attempts = 0
                while (cur <= now or cur.weekday() not in allowed_idx) and attempts < 400:
                    cur = cur + timedelta(days=1)
                    attempts += 1
                ev["next_due"] = cur.strftime("%Y-%m-%dT%H:%M") if use_time else cur.strftime("%Y-%m-%d")
                return f"Recurrence for '{title}' set to '{frequency}'."
            else:
                # weekly with interval
                interval_weeks = 1
                if "INTERVAL=" in rrule:
                    try:
                        interval_weeks = int(rrule.split("INTERVAL=")[1].split(";")[0])
                    except Exception:
                        interval_weeks = 1
                step = timedelta(weeks=interval_weeks)
        elif "FREQ=MONTHLY" in rrule:
            # step by months: approximate by adding 28 days until month changes, then adjust
            def add_months(dt, months):
                month = dt.month - 1 + months
                year = dt.year + month // 12
                month = month % 12 + 1
                day = min(dt.day, 28)  # avoid invalid days; keep safe default
                return datetime(year, month, day, dt.hour, dt.minute) if use_time else datetime(year, month, day)
            interval_months = 1
            if "INTERVAL=" in rrule:
                try:
                    interval_months = int(rrule.split("INTERVAL=")[1].split(";")[0])
                except Exception:
                    interval_months = 1
            attempts = 0
            while cur <= now and attempts < 120:
                cur = add_months(cur, interval_months)
                attempts += 1
            ev["next_due"] = cur.strftime("%Y-%m-%dT%H:%M") if use_time else cur.strftime("%Y-%m-%d")
            return f"Recurrence for '{title}' set to '{frequency}'."
        else:
            # fallback: daily step by 1
            step = timedelta(days=1)

        attempts = 0
        while cur <= now and attempts < 1000:
            cur = cur + step
            attempts += 1

        ev["next_due"] = cur.strftime("%Y-%m-%dT%H:%M") if use_time else cur.strftime("%Y-%m-%d")
    except Exception as exc:
        # keep recurrence but fallback to storing original date
        ev["next_due"] = ev.get("date")
        return f"Recurrence set but failed to compute next due: {exc}"

    return f"Recurrence for '{title}' set to '{frequency}'{(' (interval=' + str(interval) + ')') if key=='custom' else ''}."

import os
import re
from datetime import datetime, timedelta

def _looks_like_add_command(msg: str) -> bool:
    import re
    return bool(re.search(r'\b(add|schedule|create|event|book)\b', msg, re.I))

@mcp.tool()
def research_and_breakdown(goal: str, deadline: str = None) -> dict:
    """
    Produce a structured plan for a user goal.
    If OPENAI_API_KEY present, attempt to ask the LLM to return a JSON plan.
    Fallback: heuristic generator (already implemented below).
    """
    # Try to parse deadline if provided
    now = datetime.now()
    dt_deadline = None
    if deadline:
        try:
            # accept YYYY-MM-DD or natural-ish (try ISO)
            if 'T' in deadline:
                dt_deadline = datetime.fromisoformat(deadline)
            else:
                dt_deadline = datetime.strptime(deadline, "%Y-%m-%d")
        except Exception:
            # fallback: try parse relative like "in 3 months" not implemented — ignore
            dt_deadline = None

    # Integrate with external LLM if configured (optional)
    llm_key = os.getenv("LLM_API_KEY")
    if llm_key:
      try:
        model = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
        prompt = (
          "You are a planning assistant. Given a user goal and optional deadline, "
          "return a JSON object with keys: goal, deadline (YYYY-MM-DD or null), "
          "estimated_days (int), milestones (array of {title,due,steps}), "
          "cadence_suggestions (array of strings). "
          "Each milestone.steps should be a short list of actionable tasks. "
          "Only emit pure JSON."
          f"\n\nGoal: {goal}\nDeadline: {deadline or 'none'}\n\n"
          "Return the JSON without extra commentary."
        )
        headers = {
          "Authorization": f"Bearer {llm_key}",
          "Content-Type": "application/json",
        }
        payload = {
          "model": model,
          "messages": [
            {"role": "system", "content": "You output only JSON."},
            {"role": "user", "content": prompt},
          ],
          "temperature": 0.2,
          "max_tokens": 800,
        }
        resp = httpx.post(
          "https://openrouter.ai/api/v1/chat/completions",
          json=payload,
          headers=headers,
          timeout=20.0,
        )
        if resp.status_code == 200:
          body = resp.json()
          text = body.get("choices", [{}])[0].get("message", {}).get("content", "")
          try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "milestones" in parsed:
              return parsed
          except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
              try:
                parsed = json.loads(text[start:end+1])
                if isinstance(parsed, dict) and "milestones" in parsed:
                  return parsed
              except Exception:
                pass
        # fall through to heuristic if LLM response unusable
      except Exception:
        pass

    # Heuristic breakdown generator
    # Choose between 3 and 6 milestones depending on time available
    if dt_deadline:
        total_days = max(1, (dt_deadline - now).days)
    else:
        total_days = 30  # default planning horizon
        dt_deadline = now + timedelta(days=total_days)

    # decide number of milestones: 3 for short, up to 6 for longer horizons
    if total_days <= 14:
        n = 3
    elif total_days <= 60:
        n = 4
    elif total_days <= 180:
        n = 5
    else:
        n = 6

    days_per_milestone = max(1, total_days // n)
    milestones = []
    cur = now
    for i in range(1, n + 1):
        cur = cur + timedelta(days=days_per_milestone)
        m_title = f"Milestone {i}: {goal.split()[0:3] and ' '.join(goal.split()[0:3]) or 'Step'}"
        milestones.append({
          "title": m_title,
          "due": cur.strftime("%Y-%m-%d"),
          "steps": [
            "Clarify requirements",
            "Draft a quick plan",
            "Build the first version",
          ],
        })

    # cadence suggestions based on total days
    cadence = []
    if total_days <= 14:
        cadence = ["daily", "every other day"]
    elif total_days <= 60:
        cadence = ["every other day", "weekly"]
    else:
        cadence = ["weekly", "biweekly"]

    result = {
        "goal": goal,
        "deadline": dt_deadline.strftime("%Y-%m-%d") if dt_deadline else None,
        "estimated_days": total_days,
        "milestones": milestones,
        "cadence_suggestions": cadence,
        "note": "Use 'set_recurrence' to apply cadence to created sub-tasks or accept and create tasks manually."
    }
    return result

# New server-side tool: create_tasks from a plan
@mcp.tool()
def create_tasks(plan: dict) -> str:
  """
  Create calendar events from a structured plan object (as returned by `research_and_breakdown`).
  """
  if not isinstance(plan, dict):
    return "Invalid plan payload. Expected a JSON object with milestones."

  milestones = plan.get("milestones") or []
  if not isinstance(milestones, list) or not milestones:
    return "No milestones found in plan."

  def _normalize_due(raw_due: str) -> str:
    if not isinstance(raw_due, str):
      return ""
    due = raw_due.strip()
    if not due:
      return ""

    known_formats = (
      "%Y-%m-%d",
      "%Y-%m-%d %H:%M",
      "%Y-%m-%dT%H:%M",
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%dT%H:%M:%S",
      "%Y-%m-%dT%H:%M:%SZ",
    )
    for fmt in known_formats:
      try:
        dt = datetime.strptime(due, fmt)
        if "%H" in fmt:
          return dt.strftime("%Y-%m-%dT%H:%M")
        return dt.strftime("%Y-%m-%d")
      except Exception:
        pass

    try:
      iso = due.replace("Z", "+00:00")
      dt = datetime.fromisoformat(iso)
      if any(sep in due for sep in ("T", " ")):
        return dt.strftime("%Y-%m-%dT%H:%M")
      return dt.strftime("%Y-%m-%d")
    except Exception:
      return ""

  goal = plan.get("goal") or ""
  created = 0
  skipped = 0

  for m in milestones:
    if not isinstance(m, dict):
      skipped += 1
      continue
    title = (m.get("title") or "Milestone").strip()
    due = _normalize_due(m.get("due") or m.get("date") or "")
    if not due:
      skipped += 1
      continue
    steps = m.get("steps") if isinstance(m.get("steps"), list) else []
    student_name = str(m.get("student") or plan.get("student") or "").strip()
    student_objective = str(m.get("objective") or plan.get("student_objective") or "").strip()
    checklist = [f"- {str(step).strip()}" for step in steps if isinstance(step, str) and str(step).strip()]
    desc_lines = []
    if goal:
      desc_lines.append(f"Goal: {goal}")
    if student_name:
      desc_lines.append(f"Student: {student_name}")
    if student_objective:
      desc_lines.append(f"Personalized objective: {student_objective}")
    if m.get("description"):
      desc_lines.append(str(m.get("description")).strip())
    if checklist:
      desc_lines.append("What needs to be completed:")
      desc_lines.extend(checklist)
    desc = "\n".join(desc_lines).strip()

    before_len = len(events)
    add_event(title=title, date=due, description=desc)
    if len(events) > before_len:
      events[-1]["milestone"] = True
      events[-1]["source"] = "plan_milestone"
      if student_name:
        events[-1]["student"] = student_name
      if student_objective:
        events[-1]["student_objective"] = student_objective
      created += 1
    else:
      skipped += 1

  return f"Created {created} milestone event(s). Skipped {skipped}. These are now included in /export.ics."
