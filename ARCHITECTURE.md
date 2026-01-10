# Architecture Documentation

## System Overview

The Calendar MCP Server is a serverless application built on the Model Context Protocol (MCP) that provides calendar event management capabilities through a RESTful API interface.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
├─────────────────────────────────────────────────────────────┤
│  • AI Assistants (Claude, ChatGPT, etc.)                    │
│  • HTTP Clients (curl, Postman, etc.)                       │
│  • Web Applications                                          │
│  • Mobile Applications                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTP POST (JSON)
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                   Vercel Platform                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Serverless Function (api/mcp.py)             │   │
│  │                                                       │   │
│  │  • Request Validation                                │   │
│  │  • HTTP Method Check (POST only)                     │   │
│  │  • JSON Payload Parsing                              │   │
│  │  • Tool Name Extraction                              │   │
│  │  • Error Handling                                    │   │
│  │  • Response Formatting                               │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
└──────────────────────┼───────────────────────────────────────┘
                       │
                       │ async call
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              MCP Server Layer (main.py)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │            FastMCP Server Instance                   │   │
│  │                                                       │   │
│  │  • Tool Registration                                 │   │
│  │  • Prompt Registration                               │   │
│  │  • Request Routing                                   │   │
│  │  • Tool Execution                                    │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼──────────────────────────────────┐  │
│  │                MCP Tools                              │  │
│  │                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │  add_event   │  │ view_events  │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  │                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │delete_event  │  │   Prompts    │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                       │
└──────────────────────┼───────────────────────────────────────┘
                       │
                       │ read/write
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                 Data Layer                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │         In-Memory Storage (events list)             │   │
│  │                                                       │   │
│  │  [                                                   │   │
│  │    {                                                 │   │
│  │      "title": "Team Meeting",                       │   │
│  │      "date": "2026-01-15",                          │   │
│  │      "description": "Quarterly planning"            │   │
│  │    },                                                │   │
│  │    ...                                               │   │
│  │  ]                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Client Layer

**Purpose**: Interface for users and applications to interact with the calendar system

**Components**:
- AI Assistants (Claude, GPT-4, etc.)
- HTTP clients (curl, Postman, JavaScript fetch)
- Web and mobile applications

**Communication**:
- Protocol: HTTPS
- Format: JSON
- Method: POST

### 2. Vercel Platform

**Purpose**: Serverless hosting and request management

**Features**:
- Automatic scaling
- Global CDN distribution
- SSL/TLS termination
- Request routing
- Environment variable management

**Configuration** (`vercel.json`):
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" }
  ]
}
```

### 3. API Handler (api/mcp.py)

**Purpose**: HTTP request/response handling and routing

**Responsibilities**:
- Validate HTTP method (POST only)
- Parse JSON request body
- Extract tool name and parameters
- Route to appropriate MCP tool
- Handle errors and exceptions
- Format responses as JSON

**Request Flow**:
1. Receive HTTP POST request
2. Validate request method
3. Parse JSON payload
4. Extract `tool` and `input` fields
5. Call MCP tool with parameters
6. Unwrap MCP response content
7. Return JSON response

**Error Handling**:
- 405: Method not allowed (non-POST requests)
- 400: Bad request (missing tool name)
- 500: Internal server error (tool execution failures)

### 4. MCP Server (main.py)

**Purpose**: Core business logic and event management

**Framework**: FastMCP
- Lightweight MCP server implementation
- Decorator-based tool registration
- Automatic parameter validation
- Response formatting

**Components**:

#### Tool Registry
- `add_event`: Create new calendar events
- `view_events`: List all events chronologically
- `delete_event`: Remove events by title

#### Prompt Registry
- `summarize_events`: Generate event summaries for AI consumption

#### Event Storage
- In-memory Python list
- No persistence between server restarts
- Fast read/write access
- Thread-unsafe (single execution context)

### 5. Data Layer

**Current Implementation**: In-Memory Storage

**Structure**:
```python
events: List[Dict] = [
    {
        "title": str,
        "date": str,        # YYYY-MM-DD format
        "description": str  # Optional
    }
]
```

**Characteristics**:
- ✅ Fast access (O(1) append, O(n) search)
- ✅ Simple implementation
- ✅ No external dependencies
- ❌ No persistence
- ❌ Not thread-safe
- ❌ Limited to single server instance

## Data Flow

### Adding an Event

```
1. Client sends POST request:
   {
     "tool": "add_event",
     "input": {
       "title": "Meeting",
       "date": "2026-01-15",
       "description": "Planning"
     }
   }

2. Vercel routes to api/mcp.py handler

3. Handler validates request:
   - Check method == "POST"
   - Parse JSON body
   - Extract tool name and inputs

4. Handler calls MCP tool:
   await main.mcp.call_tool("add_event", {...})

5. MCP server executes add_event:
   - Validate date format
   - Create event dict
   - Append to events list
   - Return success message

6. Handler unwraps MCP response:
   result.text → "Event 'Meeting' added for 2026-01-15."

7. Handler returns JSON:
   {
     "statusCode": 200,
     "body": {"result": "Event 'Meeting' added for 2026-01-15."}
   }

8. Client receives response
```

### Viewing Events

```
1. Client sends POST request:
   {
     "tool": "view_events",
     "input": {}
   }

2. Handler routes to view_events tool

3. Tool retrieves events from memory:
   - Check if events list is empty
   - Sort events by date
   - Format as readable string

4. Return formatted event list:
   "Calendar Events:\n- 2026-01-15: Meeting - Planning\n"
```

## Design Patterns

### 1. Serverless Architecture Pattern
- Stateless request handling
- Auto-scaling based on demand
- Pay-per-execution pricing model

### 2. Adapter Pattern
- API handler adapts HTTP requests to MCP protocol
- Translates between REST and MCP interfaces

### 3. Decorator Pattern
- FastMCP uses decorators (@mcp.tool, @mcp.prompt)
- Declarative tool registration
- Separation of concerns

### 4. In-Memory Repository Pattern
- Events list acts as simple repository
- Direct access without abstraction layer
- Fast but non-persistent

## Performance Considerations

### Current Performance

**Strengths**:
- Fast response times (~10-50ms for simple operations)
- Minimal latency (in-memory operations)
- No database query overhead
- Automatic scaling via Vercel

**Limitations**:
- Cold start latency (~100-500ms)
- No caching between requests
- No query optimization needed (small dataset)
- Single-threaded execution

### Scalability

**Horizontal Scaling**:
- ✅ Each Vercel function invocation is independent
- ❌ No shared state between instances
- ❌ Events not synchronized across instances

**Vertical Scaling**:
- Limited by Vercel function memory/CPU limits
- Not applicable for in-memory storage

**Current Limits**:
- Suitable for: Development, demos, single-user scenarios
- Not suitable for: Production, multi-user, persistent data

## Security Considerations

### Current Implementation

**Authentication**: None
- All endpoints are public
- No user identity verification
- No access control

**Input Validation**:
- Date format validation (YYYY-MM-DD)
- JSON parsing with error handling
- No SQL injection risk (no database)

**Data Security**:
- In-memory only (no disk persistence)
- Data lost on server restart
- No encryption at rest
- HTTPS encryption in transit (via Vercel)

### Future Security Enhancements

See [CALENDAR_SYNC.md](CALENDAR_SYNC.md) for OAuth 2.0 authentication design.

**Planned**:
- OAuth 2.0 authentication
- JWT token validation
- Rate limiting
- Input sanitization
- CORS configuration
- API key management

## Testing Strategy

### Current Testing

**Local Testing** (`test_local.py`):
- Mock HTTP request object
- Direct handler invocation
- Manual verification

**Test Coverage**:
- Basic add_event functionality
- No automated test suite
- No CI/CD integration

### Future Testing

**Unit Tests**:
- Test each MCP tool independently
- Mock data layer
- Validate error handling

**Integration Tests**:
- Test full request/response cycle
- Test API handler integration
- Test Vercel deployment

**End-to-End Tests**:
- Test deployed API endpoints
- Validate real HTTP requests
- Monitor production behavior

## Deployment

### Vercel Deployment

**Requirements**:
- `vercel.json` configuration
- Python runtime
- Requirements.txt for dependencies

**Process**:
1. Push code to GitHub
2. Vercel auto-deploys on push (if configured)
3. Or manually deploy: `vercel`
4. Function deployed at `/api/mcp`

**Environment**:
- Runtime: Python 3.12
- Region: Auto (nearest to user)
- Memory: Default (1024 MB)
- Timeout: 10 seconds (default)

### Configuration Files

**vercel.json**:
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" }
  ]
}
```

**pyproject.toml**:
- Project metadata
- Python version requirement
- No dependencies currently

**requirements.txt**:
- Auto-generated from pyproject.toml
- Currently empty (no external deps)

## Error Handling

### API Handler Errors

**HTTP 405 - Method Not Allowed**:
- Trigger: Non-POST request
- Response: `{"error": "Method not allowed"}`

**HTTP 400 - Bad Request**:
- Trigger: Missing tool name in payload
- Response: `{"error": "Missing tool name"}`

**HTTP 500 - Internal Server Error**:
- Trigger: Tool execution exception
- Response: `{"error": "<exception message>"}`

### Tool-Level Errors

**add_event Validation**:
- Invalid date format
- Returns error string (not HTTP error)

**delete_event Not Found**:
- Event doesn't exist
- Returns "No event found" message

## Monitoring and Logging

### Current State

**Logging**: Minimal
- No structured logging
- No request/response logging
- Python print statements only

**Monitoring**: Vercel default
- Function invocation count
- Error rate
- Response time
- No custom metrics

### Future Enhancements

**Logging**:
- Structured JSON logs
- Request ID tracking
- Performance metrics
- Error stack traces

**Monitoring**:
- Custom metrics (events created, deleted)
- Alerting on errors
- Performance dashboards
- Usage analytics

## Future Architecture

See [CALENDAR_SYNC.md](CALENDAR_SYNC.md) for detailed future architecture including:
- OAuth 2.0 authentication flow
- External calendar API integration
- Database persistence layer
- Caching strategy
- Background sync jobs
