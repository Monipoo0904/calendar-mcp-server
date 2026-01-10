# API Reference

Complete reference for the Calendar MCP Server API.

## Table of Contents

1. [HTTP API](#http-api)
2. [MCP Tools](#mcp-tools)
3. [MCP Prompts](#mcp-prompts)
4. [Error Codes](#error-codes)
5. [Data Models](#data-models)
6. [Examples](#examples)

---

## HTTP API

### Base URL

**Production**: `https://your-project.vercel.app`  
**Local Development**: `http://localhost:3000`

### Authentication

Current version: **No authentication required** (public API)

Future version: OAuth 2.0 Bearer token authentication

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Common Headers

```
Content-Type: application/json
Accept: application/json
```

---

## Endpoint: POST /api/mcp

Execute MCP tools via HTTP POST requests.

### Request Format

```json
{
  "tool": "string",
  "input": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

### Response Format

**Success Response (200 OK)**:
```json
{
  "result": "string"
}
```

**Error Responses**:

**400 Bad Request**:
```json
{
  "error": "Missing tool name"
}
```

**405 Method Not Allowed**:
```json
{
  "error": "Method not allowed"
}
```

**500 Internal Server Error**:
```json
{
  "error": "Error message describing what went wrong"
}
```

---

## MCP Tools

### add_event

Add a new calendar event.

**Tool Name**: `add_event`

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `title` | string | Yes | Event title/name |
| `date` | string | Yes | Event date in YYYY-MM-DD format |
| `description` | string | No | Event description/notes (default: empty string) |

**Date Format**: ISO 8601 date format (YYYY-MM-DD)
- Valid examples: `2026-01-15`, `2026-12-31`
- Invalid examples: `01-15-2026`, `2026/01/15`, `15-01-2026`

**Returns**: Success message string

**Success Response**:
```
"Event 'Team Meeting' added for 2026-01-15."
```

**Error Response**:
```
"Invalid date format. Use YYYY-MM-DD."
```

**HTTP Example**:

```bash
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_event",
    "input": {
      "title": "Team Meeting",
      "date": "2026-01-15",
      "description": "Quarterly planning session"
    }
  }'
```

**Response**:
```json
{
  "result": "Event 'Team Meeting' added for 2026-01-15."
}
```

**Notes**:
- Events are stored in-memory (lost on server restart)
- No duplicate checking (same title/date can be added multiple times)
- Title and description have no length limits (current implementation)

---

### view_events

View all calendar events in chronological order.

**Tool Name**: `view_events`

**Parameters**: None

**Returns**: Formatted string with all events

**Empty Calendar Response**:
```
"No events scheduled."
```

**With Events Response**:
```
"Calendar Events:
- 2026-01-15: Team Meeting - Quarterly planning session
- 2026-02-20: Dentist Appointment
- 2026-03-10: Conference - Annual tech conference
"
```

**HTTP Example**:

```bash
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "view_events",
    "input": {}
  }'
```

**Response**:
```json
{
  "result": "Calendar Events:\n- 2026-01-15: Team Meeting - Quarterly planning session\n- 2026-02-20: Dentist Appointment\n"
}
```

**Notes**:
- Events are automatically sorted by date (earliest first)
- Description is only shown if it exists
- Format: `- DATE: TITLE - DESCRIPTION` or `- DATE: TITLE`

---

### delete_event

Delete an event by its title.

**Tool Name**: `delete_event`

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `title` | string | Yes | Title of event to delete (case-insensitive) |

**Returns**: Success or error message string

**Success Response**:
```
"Event 'Team Meeting' deleted."
```

**Not Found Response**:
```
"No event found with title 'Team Meeting'."
```

**HTTP Example**:

```bash
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "delete_event",
    "input": {
      "title": "Team Meeting"
    }
  }'
```

**Response**:
```json
{
  "result": "Event 'Team Meeting' deleted."
}
```

**Notes**:
- Case-insensitive matching: `"Team Meeting"` = `"team meeting"` = `"TEAM MEETING"`
- If multiple events have the same title, **all** are deleted
- No confirmation prompt (deletion is immediate)
- Cannot be undone (no soft delete)

---

## MCP Prompts

### summarize_events

Generate a summary of all upcoming events.

**Prompt Name**: `summarize_events`

**Note**: This is an MCP **prompt**, not a tool. Prompts are designed for AI assistant consumption and may not be directly callable via the HTTP API depending on your MCP client implementation.

**Parameters**: None

**Returns**: Formatted summary string

**Empty Calendar Response**:
```
"No events scheduled."
```

**With Events Response**:
```
"Upcoming Events Summary:
- 2026-01-15: Team Meeting (Quarterly planning session)
- 2026-02-20: Dentist Appointment
- 2026-03-10: Conference (Annual tech conference)
"
```

**Format**: 
- `- DATE: TITLE (DESCRIPTION)` if description exists
- `- DATE: TITLE` if no description

**Use Cases**:
- Provide context to AI assistants
- Generate calendar summaries for reports
- Quick overview of scheduled events

---

## Error Codes

### HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful, result in response body |
| 400 | Bad Request | Invalid request format or missing required fields |
| 405 | Method Not Allowed | HTTP method other than POST was used |
| 500 | Internal Server Error | Tool execution error or server error |

### Tool-Level Errors

Tool errors are returned with HTTP 200 status but contain error messages in the `result` field:

**Date Validation Error** (add_event):
```json
{
  "result": "Invalid date format. Use YYYY-MM-DD."
}
```

**Event Not Found** (delete_event):
```json
{
  "result": "No event found with title 'Nonexistent Event'."
}
```

**Tool Not Found**:
```json
{
  "error": "Unknown tool: invalid_tool_name"
}
```

**Missing Required Parameter**:
```json
{
  "error": "Missing required parameter: title"
}
```

---

## Data Models

### Event Object

Events are stored internally as dictionaries with the following structure:

```python
{
    "title": str,        # Event title/name
    "date": str,         # Date in YYYY-MM-DD format
    "description": str   # Event description (may be empty string)
}
```

**Example**:
```python
{
    "title": "Team Meeting",
    "date": "2026-01-15",
    "description": "Quarterly planning session"
}
```

**Constraints**:
- `title`: Required, non-empty string
- `date`: Required, valid ISO 8601 date (YYYY-MM-DD)
- `description`: Optional, defaults to empty string

### HTTP Request Object

```json
{
    "tool": "string",     // Required: Tool name to execute
    "input": {            // Required: Tool parameters (may be empty object)
        "param1": "value1",
        "param2": "value2"
    }
}
```

### HTTP Response Object

**Success**:
```json
{
    "result": "string"    // Tool output
}
```

**Error**:
```json
{
    "error": "string"     // Error message
}
```

---

## Examples

### Example 1: Add Multiple Events

```bash
# Add first event
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_event",
    "input": {
      "title": "Morning Standup",
      "date": "2026-01-15",
      "description": "Daily team sync"
    }
  }'

# Add second event
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_event",
    "input": {
      "title": "Client Meeting",
      "date": "2026-01-16"
    }
  }'

# View all events
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "view_events",
    "input": {}
  }'
```

### Example 2: Event Lifecycle

```bash
# 1. Add an event
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_event",
    "input": {
      "title": "Temporary Event",
      "date": "2026-01-20"
    }
  }'

# Response: {"result": "Event 'Temporary Event' added for 2026-01-20."}

# 2. View events to confirm
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "view_events",
    "input": {}
  }'

# Response: {"result": "Calendar Events:\n- 2026-01-20: Temporary Event\n"}

# 3. Delete the event
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "delete_event",
    "input": {
      "title": "Temporary Event"
    }
  }'

# Response: {"result": "Event 'Temporary Event' deleted."}

# 4. Verify deletion
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "view_events",
    "input": {}
  }'

# Response: {"result": "No events scheduled."}
```

### Example 3: Error Handling

```bash
# Invalid date format
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_event",
    "input": {
      "title": "Invalid Event",
      "date": "01-15-2026"
    }
  }'

# Response: {"result": "Invalid date format. Use YYYY-MM-DD."}

# Invalid HTTP method
curl -X GET https://your-app.vercel.app/api/mcp

# Response: {"error": "Method not allowed"}

# Missing tool name
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "title": "Event"
    }
  }'

# Response: {"error": "Missing tool name"}

# Unknown tool
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "nonexistent_tool",
    "input": {}
  }'

# Response: {"error": "Unknown tool: nonexistent_tool"}
```

### Example 4: JavaScript/TypeScript

```typescript
// add_event function
async function addEvent(
  title: string,
  date: string,
  description: string = ""
): Promise<string> {
  const response = await fetch("https://your-app.vercel.app/api/mcp", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tool: "add_event",
      input: { title, date, description },
    }),
  });

  const data = await response.json();
  
  if (response.ok) {
    return data.result;
  } else {
    throw new Error(data.error || "Unknown error");
  }
}

// view_events function
async function viewEvents(): Promise<string> {
  const response = await fetch("https://your-app.vercel.app/api/mcp", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tool: "view_events",
      input: {},
    }),
  });

  const data = await response.json();
  
  if (response.ok) {
    return data.result;
  } else {
    throw new Error(data.error || "Unknown error");
  }
}

// delete_event function
async function deleteEvent(title: string): Promise<string> {
  const response = await fetch("https://your-app.vercel.app/api/mcp", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tool: "delete_event",
      input: { title },
    }),
  });

  const data = await response.json();
  
  if (response.ok) {
    return data.result;
  } else {
    throw new Error(data.error || "Unknown error");
  }
}

// Usage example
async function main() {
  try {
    // Add events
    await addEvent("Team Meeting", "2026-01-15", "Quarterly planning");
    await addEvent("Dentist", "2026-02-20");
    
    // View all events
    const events = await viewEvents();
    console.log(events);
    
    // Delete an event
    await deleteEvent("Dentist");
    
  } catch (error) {
    console.error("Error:", error.message);
  }
}
```

### Example 5: Python Client

```python
import httpx
import asyncio
from typing import Optional

class CalendarMCPClient:
    def __init__(self, base_url: str = "https://your-app.vercel.app"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/mcp"
    
    async def _call_tool(self, tool: str, input_data: dict) -> str:
        """Helper method to call MCP tools."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint,
                json={"tool": tool, "input": input_data},
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise Exception(data["error"])
            
            return data["result"]
    
    async def add_event(
        self,
        title: str,
        date: str,
        description: str = ""
    ) -> str:
        """Add a calendar event."""
        return await self._call_tool("add_event", {
            "title": title,
            "date": date,
            "description": description
        })
    
    async def view_events(self) -> str:
        """View all calendar events."""
        return await self._call_tool("view_events", {})
    
    async def delete_event(self, title: str) -> str:
        """Delete an event by title."""
        return await self._call_tool("delete_event", {"title": title})


# Usage example
async def main():
    client = CalendarMCPClient()
    
    # Add events
    result = await client.add_event(
        "Team Meeting",
        "2026-01-15",
        "Quarterly planning"
    )
    print(result)
    
    # View events
    events = await client.view_events()
    print(events)
    
    # Delete event
    result = await client.delete_event("Team Meeting")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Rate Limits

**Current**: No rate limiting

**Future**: 
- 100 requests per minute per IP address
- 1000 requests per hour per user (with authentication)
- Burst allowance: 20 requests

Rate limit headers (future):
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1641024000
```

---

## Pagination

**Current**: Not supported (all events returned)

**Future**: Pagination for view_events tool:

```json
{
  "tool": "view_events",
  "input": {
    "page": 1,
    "per_page": 20
  }
}
```

Response:
```json
{
  "result": {
    "events": [...],
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

---

## Versioning

**Current Version**: v1 (implicit, no version in URL)

**Future**: Version in URL path:
- `/api/v1/mcp` - Stable API
- `/api/v2/mcp` - New features with breaking changes

---

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/Monipoo0904/calendar-mcp-server/issues
- Email: [repository maintainer email]

---

## Related Documentation

- [README.md](README.md) - Getting started guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [CALENDAR_SYNC.md](CALENDAR_SYNC.md) - OAuth 2.0 and sync features
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines

---

**Last Updated**: January 2026  
**API Version**: 0.1.0
