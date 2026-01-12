from mcp.server.fastmcp import FastMCP 
from typing import List, Dict 
from datetime import datetime 
from oauth_handler import oauth_handler

# Create an MCP server 
mcp = FastMCP("EventCalendar") 


# In-memory storage for events 
# Each event is a dict: {"title": str, "date": str, "description": str} 
events: List[Dict] = []


# OAuth and authentication tools
@mcp.tool()
def get_consent_prompt() -> str:
    """
    Get the consent message asking for permission to access calendar and email.
    This should be shown to the user before starting the OAuth flow.
    """
    return oauth_handler.get_consent_message()


@mcp.tool()
def start_oauth_flow() -> str:
    """
    Start the OAuth 2.0 authentication flow.
    Returns the authorization URL that the user needs to visit.
    """
    try:
        auth_url = oauth_handler.get_authorization_url()
        return (
            f"Please visit the following URL to authorize access:\n\n{auth_url}\n\n"
            "After authorizing, you will receive a code. Use the 'complete_oauth_flow' tool with that code."
        )
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error starting OAuth flow: {str(e)}"


@mcp.tool()
def complete_oauth_flow(authorization_code: str) -> str:
    """
    Complete the OAuth 2.0 flow by exchanging the authorization code for tokens.
    
    Args:
        authorization_code: The authorization code received after user consent
    """
    success = oauth_handler.exchange_code_for_token(authorization_code)
    if success:
        return oauth_handler.get_welcome_message()
    else:
        return "Failed to complete authentication. Please try again."


@mcp.tool()
def get_welcome_message() -> str:
    """
    Get the welcome message with the user's first name.
    Returns authentication status if not authenticated.
    """
    if oauth_handler.load_credentials() or oauth_handler.is_authenticated():
        return oauth_handler.get_welcome_message()
    else:
        return "You are not authenticated. Please use 'get_consent_prompt' and 'start_oauth_flow' to begin authentication."


@mcp.tool()
def check_authentication_status() -> str:
    """
    Check if the user is currently authenticated.
    """
    oauth_handler.load_credentials()
    if oauth_handler.is_authenticated():
        first_name = oauth_handler.get_user_first_name()
        if first_name:
            return f"Authenticated as {first_name}"
        return "Authenticated"
    else:
        return "Not authenticated. Please complete the OAuth flow first." 

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

if __name__ == "__main__": 
  mcp.run() 

