# Calendar MCP Server

A Model Context Protocol (MCP) server for managing calendar events, designed for deployment on Vercel as a serverless API.

## Overview

This project implements a calendar event management system using the MCP protocol, allowing AI assistants and other clients to create, read, update, and delete calendar events through a standardized interface.

### Key Features

- **Event Management**: Add, view, and delete calendar events
- **Event Summaries**: Generate formatted summaries of upcoming events
- **MCP Protocol**: Standardized interface for AI assistant integration
- **Serverless Deployment**: Ready for Vercel deployment
- **RESTful API**: HTTP POST endpoint for tool execution

### Current Implementation

The current version provides basic calendar functionality with in-memory storage:
- Add events with title, date, and optional description
- View all events in chronological order
- Delete events by title (case-insensitive)
- Generate event summaries for AI consumption

## Installation

### Prerequisites

- Python 3.12 or higher
- pip or uv package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Monipoo0904/calendar-mcp-server.git
cd calendar-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or using uv:
```bash
uv pip install -r requirements.txt
```

## Usage

### Local Development

Run the MCP server locally:
```bash
python main.py
```

### Local Testing

Test the API handler locally without deploying:
```bash
python test_local.py
```

This will execute a test request to add an event and display the response.

### Vercel Deployment

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
vercel
```

3. The API will be available at:
```
https://your-project.vercel.app/api/mcp
```

## API Reference

### HTTP Endpoint

**URL**: `/api/mcp`  
**Method**: `POST`  
**Content-Type**: `application/json`

### Request Format

```json
{
  "tool": "tool_name",
  "input": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

### Response Format

**Success (200)**:
```json
{
  "result": "Tool output string"
}
```

**Error (400/405/500)**:
```json
{
  "error": "Error message"
}
```

## Available Tools

### 1. add_event

Add a new calendar event.

**Parameters**:
- `title` (string, required): Event title/name
- `date` (string, required): Event date in YYYY-MM-DD format
- `description` (string, optional): Event description/notes

**Example**:
```bash
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_event",
    "input": {
      "title": "Team Meeting",
      "date": "2026-01-15",
      "description": "Quarterly planning"
    }
  }'
```

**Response**:
```json
{
  "result": "Event 'Team Meeting' added for 2026-01-15."
}
```

### 2. view_events

View all calendar events in chronological order.

**Parameters**: None

**Example**:
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
  "result": "Calendar Events:\n- 2026-01-15: Team Meeting - Quarterly planning\n- 2026-02-20: Dentist Appointment\n"
}
```

### 3. delete_event

Delete an event by title (case-insensitive).

**Parameters**:
- `title` (string, required): Title of event to delete

**Example**:
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

### 4. summarize_events

Generate a summary of all events (MCP prompt, not a tool).

This is designed for AI assistant consumption rather than direct API calls.

## Architecture

### Current Architecture

```
┌─────────────────────┐
│   Client Request    │
│   (HTTP POST)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Vercel Handler    │
│   (api/mcp.py)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   MCP Server        │
│   (main.py)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  In-Memory Storage  │
│  (events list)      │
└─────────────────────┘
```

### Component Descriptions

- **api/mcp.py**: Vercel serverless function handler that receives HTTP requests and routes them to MCP tools
- **main.py**: Core MCP server with event management tools and business logic
- **test_local.py**: Local testing script for development and debugging

## Data Storage

### Current: In-Memory Storage

Events are stored in a Python list in memory:
- Fast read/write operations
- No persistence (data lost on restart)
- Suitable for development and testing
- Not recommended for production

### Event Data Structure

```python
{
  "title": str,        # Event title/name
  "date": str,         # Date in YYYY-MM-DD format
  "description": str   # Optional description
}
```

## Future Enhancements

See [CALENDAR_SYNC.md](CALENDAR_SYNC.md) for detailed documentation on planned calendar synchronization features.

### Planned Features

1. **Calendar Synchronization**
   - OAuth 2.0 authentication
   - Google Calendar integration
   - Microsoft Outlook integration
   - Bidirectional sync

2. **ICS File Support**
   - Import events from .ics files
   - Export events to .ics format
   - Fallback option when API sync unavailable

3. **Persistent Storage**
   - Database backend (PostgreSQL, MongoDB)
   - Event history and audit logs
   - Backup and restore functionality

4. **Advanced Features**
   - Recurring events
   - Event reminders and notifications
   - Time zones support
   - Event categories and tags
   - Conflict detection

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## License

This project is open source. Please check the repository for license details.

## Documentation

- [Architecture Documentation](ARCHITECTURE.md) - System design and component details
- [Calendar Sync Documentation](CALENDAR_SYNC.md) - OAuth 2.0 and API integration plans
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Contributing Guidelines](CONTRIBUTING.md) - Development and contribution guide

## Support

For issues, questions, or feature requests, please open an issue on the GitHub repository.

## Project Status

**Current Version**: 0.1.0  
**Status**: Active Development  
**Last Updated**: January 2026
