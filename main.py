"""
Calendar MCP Server - Main Application Module

This module implements a Model Context Protocol (MCP) server for managing calendar events.
It provides tools for adding, viewing, and deleting events, as well as generating event summaries.

Current Implementation:
- In-memory event storage (data is not persisted between server restarts)
- Basic CRUD operations for calendar events
- Date validation using ISO 8601 format (YYYY-MM-DD)

Future Enhancements (Planned, Not Yet Implemented):
- OAuth 2.0 authentication for calendar API integration
- Google Calendar and Outlook Calendar synchronization
- .ics file import/export functionality
- Persistent storage with database backend
"""

from mcp.server.fastmcp import FastMCP 
from typing import List, Dict 
from datetime import datetime 

# Create an MCP server instance
# FastMCP provides the framework for exposing tools and prompts via the MCP protocol
mcp = FastMCP("EventCalendar") 


# In-memory storage for events
# Data structure: Each event is a dictionary with the following keys:
#   - title: str - The name/title of the event
#   - date: str - Event date in YYYY-MM-DD format (ISO 8601)
#   - description: str - Optional event description/details
# Note: Events are stored in memory only. They will be lost when the server restarts.
# Future: Implement persistent storage (database or file-based) for production use.
events: List[Dict] = [] 

# ============================================================================
# MCP Tool: add_event
# ============================================================================
@mcp.tool() 
def add_event(title: str, date: str, description: str = "") -> str: 
  """
  Add a new calendar event to the in-memory event store.
  
  This tool validates the date format and creates a new event entry.
  Events are stored in chronological order when displayed.
  
  Args:
    title: The event title/name (required)
    date: Event date in YYYY-MM-DD format (ISO 8601) (required)
    description: Optional description or notes about the event (default: empty string)
  
  Returns:
    str: Success message with event details, or error message if validation fails
  
  Examples:
    add_event("Team Meeting", "2026-01-15", "Quarterly planning session")
    add_event("Dentist Appointment", "2026-02-20")
  
  Validation:
    - Date must be in YYYY-MM-DD format
    - Invalid dates (e.g., "2026-13-45") will be rejected
  
  Future Enhancement:
    - Validate against calendar API availability
    - Check for conflicting events
    - Support recurring events
    - Sync with external calendars via OAuth 2.0
  """ 
  try: 
    # Validate date format using datetime parsing
    # This ensures the date is both correctly formatted and a valid calendar date
    datetime.strptime(date, "%Y-%m-%d") 
    
    # Append the new event to the in-memory storage
    events.append({"title": title, "date": date, "description": description}) 
    
    return f"Event '{title}' added for {date}." 
  except ValueError: 
    # Return user-friendly error message for invalid date format
    return "Invalid date format. Use YYYY-MM-DD." 
# ============================================================================
# MCP Tool: view_events
# ============================================================================
@mcp.tool() 
def view_events() -> str: 
  """
  Retrieve and display all calendar events in chronological order.
  
  This tool returns a formatted list of all events currently stored in memory.
  Events are automatically sorted by date (earliest first).
  
  Returns:
    str: Formatted string containing all events, or message if no events exist
    
  Output Format:
    Calendar Events:
    - YYYY-MM-DD: Event Title - Description
    - YYYY-MM-DD: Another Event
    
  Examples:
    Returns "No events scheduled." if the calendar is empty
    Returns formatted list of events if events exist
  
  Future Enhancement:
    - Filter events by date range
    - Filter by event category or tags
    - Paginate results for large event lists
    - Include events from synchronized external calendars
  """ 
  if not events: 
    return "No events scheduled." 
  
  # Build formatted output string
  result = "Calendar Events:\n" 
  
  # Sort events chronologically by date before displaying
  # The lambda function extracts the 'date' field for sorting
  for event in sorted(events, key=lambda x: x["date"]): 
    # Include description only if it exists
    desc = f" - {event['description']}" if event['description'] else "" 
    result += f"- {event['date']}: {event['title']}{desc}\n" 
  
  return result 
# ============================================================================
# MCP Tool: delete_event
# ============================================================================
@mcp.tool() 
def delete_event(title: str) -> str: 
  """
  Delete an event from the calendar by its title.
  
  This tool performs a case-insensitive search for an event with the specified title
  and removes it from the event store. If multiple events have the same title,
  all matching events will be deleted.
  
  Args:
    title: The title of the event to delete (case-insensitive)
  
  Returns:
    str: Success message if event(s) deleted, or error message if not found
  
  Examples:
    delete_event("Team Meeting")  # Deletes event regardless of case
    delete_event("team meeting")  # Same result as above
  
  Note:
    - Title matching is case-insensitive
    - All events with matching titles will be deleted
    - No confirmation prompt is provided
  
  Future Enhancement:
    - Add confirmation prompt before deletion
    - Delete by unique event ID instead of title
    - Support soft delete (archive events)
    - Sync deletions to external calendars
  """ 
  # Store initial count to detect if any events were deleted
  initial_length = len(events) 
  
  # Use list comprehension with slice assignment to filter out matching events
  # Case-insensitive comparison: convert both to lowercase
  events[:] = [e for e in events if e["title"].lower() != title.lower()] 
  
  # Check if any events were removed by comparing lengths
  if len(events) < initial_length: 
    return f"Event '{title}' deleted." 
  else: 
    return f"No event found with title '{title}'." 

# ============================================================================
# MCP Prompt: summarize_events
# ============================================================================
@mcp.prompt() 
def summarize_events() -> str: 
  """
  Generate a concise summary of all upcoming events.
  
  This prompt (not a tool) generates a formatted summary that can be used by
  LLM clients to understand the calendar state. Unlike tools, prompts are
  designed to provide context or generate text for LLM consumption.
  
  Returns:
    str: Formatted summary of all events in chronological order
  
  Output Format:
    Upcoming Events Summary:
    - YYYY-MM-DD: Event Title (Description)
    - YYYY-MM-DD: Another Event
  
  Use Cases:
    - Provide calendar context to AI assistants
    - Generate event summaries for reports
    - Quick overview of scheduled events
  
  Future Enhancement:
    - Filter to only show future events (exclude past events)
    - Group events by month or week
    - Include event statistics (total events, upcoming in next week, etc.)
    - Summarize events from synchronized calendars
  """

  if not events: 
    return "No events scheduled." 
  
  # Build summary string
  summary = "Upcoming Events Summary:\n" 
  
  # Sort events chronologically
  for e in sorted(events, key=lambda x: x["date"]): 
    summary += f"- {e['date']}: {e['title']}" 
    
    # Include description in parentheses if available
    if e['description']: 
      summary += f" ({e['description']})" 
    
    summary += "\n" 
  
  return summary 

# ============================================================================
# Server Entry Point
# ============================================================================
if __name__ == "__main__": 
  # Start the FastMCP server
  # This runs the server in development mode, listening for MCP protocol messages
  # For production deployment (e.g., Vercel), the server is accessed via the API handler
  mcp.run()
