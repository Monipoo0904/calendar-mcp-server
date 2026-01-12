# Calendar Synchronization Feature Documentation

## Overview

This document outlines the design and implementation plan for calendar synchronization features, including OAuth 2.0 authentication, external calendar API integration, and .ics file import/export capabilities.

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [OAuth 2.0 Authentication](#oauth-20-authentication)
3. [Calendar API Integration](#calendar-api-integration)
4. [ICS File Support](#ics-file-support)
5. [Architecture Design](#architecture-design)
6. [Implementation Roadmap](#implementation-roadmap)
7. [Security Considerations](#security-considerations)

---

## Feature Overview

### Objectives

The calendar synchronization feature aims to:

1. **Authenticate users** using OAuth 2.0 with calendar providers (Google, Microsoft)
2. **Sync events bidirectionally** between our MCP server and external calendars
3. **Import/export events** using .ics format as a fallback option
4. **Maintain data consistency** across multiple calendar sources
5. **Handle conflicts** and provide merge strategies

### Use Cases

- **Personal Calendar Integration**: Sync with user's Google Calendar or Outlook
- **Team Collaboration**: Aggregate events from multiple team members
- **Calendar Migration**: Import events from .ics files
- **Backup and Export**: Export events to .ics for backup or migration
- **Offline Access**: Use .ics files when API access is unavailable

---

## OAuth 2.0 Authentication

### Supported Providers

1. **Google Calendar API**
   - Provider: Google Identity Platform
   - Scope: `https://www.googleapis.com/auth/calendar`
   - Documentation: https://developers.google.com/calendar/auth

2. **Microsoft Outlook Calendar**
   - Provider: Microsoft Identity Platform (Azure AD)
   - Scope: `Calendars.ReadWrite`
   - Documentation: https://docs.microsoft.com/en-us/graph/auth-v2-user

### OAuth 2.0 Flow

#### Authorization Code Flow (Recommended)

This flow is most secure for web applications:

```
┌─────────┐                                           ┌───────────────┐
│  User   │                                           │   Calendar    │
│ (Client)│                                           │   Provider    │
└────┬────┘                                           │ (Google/MS)   │
     │                                                 └───────┬───────┘
     │  1. Initiate OAuth                                     │
     ├──────────────────────────────────────────────────────►│
     │    GET /oauth/authorize                                │
     │    ?client_id=xxx                                      │
     │    &redirect_uri=xxx                                   │
     │    &scope=calendar.read calendar.write                 │
     │    &response_type=code                                 │
     │                                                         │
     │  2. User consent screen                                │
     │◄────────────────────────────────────────────────────── │
     │                                                         │
     │  3. User approves                                      │
     ├──────────────────────────────────────────────────────►│
     │                                                         │
     │  4. Redirect with auth code                            │
     │◄────────────────────────────────────────────────────── │
     │    GET /callback?code=AUTH_CODE                        │
     │                                                         │
┌────▼────┐                                           ┌───────▼───────┐
│   MCP   │                                           │   Calendar    │
│  Server │                                           │   Provider    │
└────┬────┘                                           └───────┬───────┘
     │  5. Exchange code for tokens                          │
     ├──────────────────────────────────────────────────────►│
     │    POST /oauth/token                                   │
     │    code=AUTH_CODE                                      │
     │    client_id=xxx                                       │
     │    client_secret=xxx                                   │
     │                                                         │
     │  6. Return access token + refresh token                │
     │◄────────────────────────────────────────────────────── │
     │    {                                                    │
     │      "access_token": "...",                            │
     │      "refresh_token": "...",                           │
     │      "expires_in": 3600                                │
     │    }                                                    │
     │                                                         │
     │  7. Use access token for API calls                     │
     ├──────────────────────────────────────────────────────►│
     │    GET /calendar/events                                │
     │    Authorization: Bearer ACCESS_TOKEN                  │
     │                                                         │
     │  8. Return calendar data                               │
     │◄────────────────────────────────────────────────────── │
     │                                                         │
```

### Implementation Components

#### 1. OAuth Endpoints

**New MCP Tools**:

```python
@mcp.tool()
def initiate_oauth(provider: str) -> str:
    """
    Start OAuth 2.0 authentication flow.
    
    Args:
        provider: "google" or "microsoft"
    
    Returns:
        Authorization URL for user to visit
    """
    pass

@mcp.tool()
def oauth_callback(code: str, state: str) -> str:
    """
    Handle OAuth callback and exchange code for tokens.
    
    Args:
        code: Authorization code from provider
        state: CSRF protection token
    
    Returns:
        Success message with user details
    """
    pass

@mcp.tool()
def refresh_token(user_id: str) -> str:
    """
    Refresh expired access token.
    
    Args:
        user_id: User identifier
    
    Returns:
        Success message
    """
    pass
```

#### 2. Token Storage

**Database Schema** (PostgreSQL example):

```sql
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP NOT NULL,
    scope TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_provider ON oauth_tokens(user_id, provider);
CREATE INDEX idx_expires_at ON oauth_tokens(expires_at);
```

#### 3. Configuration

**Environment Variables**:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-app.vercel.app/api/oauth/callback

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_REDIRECT_URI=https://your-app.vercel.app/api/oauth/callback
MICROSOFT_TENANT_ID=common

# Security
OAUTH_STATE_SECRET=random-secret-for-csrf-protection
```

#### 4. Security Measures

**CSRF Protection**:
- Generate random state parameter
- Store in session or database
- Validate on callback

**Token Security**:
- Encrypt tokens at rest
- Use HTTPS for all communications
- Implement token rotation
- Set appropriate expiration times

**Scope Limitation**:
- Request minimal necessary scopes
- Separate read and write permissions
- Allow users to revoke access

---

## Calendar API Integration

### Google Calendar API

#### Setup

1. Create project in Google Cloud Console
2. Enable Google Calendar API
3. Configure OAuth consent screen
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs

#### API Endpoints

**List Events**:
```python
GET https://www.googleapis.com/calendar/v3/calendars/primary/events
Authorization: Bearer ACCESS_TOKEN

Query Parameters:
- timeMin: RFC3339 timestamp (filter start)
- timeMax: RFC3339 timestamp (filter end)
- maxResults: Integer (pagination)
- pageToken: String (pagination)
```

**Create Event**:
```python
POST https://www.googleapis.com/calendar/v3/calendars/primary/events
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json

Body:
{
  "summary": "Event Title",
  "description": "Event Description",
  "start": {
    "dateTime": "2026-01-15T10:00:00-07:00",
    "timeZone": "America/Los_Angeles"
  },
  "end": {
    "dateTime": "2026-01-15T11:00:00-07:00",
    "timeZone": "America/Los_Angeles"
  }
}
```

**Update Event**:
```python
PUT https://www.googleapis.com/calendar/v3/calendars/primary/events/{eventId}
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json

Body: (same as create)
```

**Delete Event**:
```python
DELETE https://www.googleapis.com/calendar/v3/calendars/primary/events/{eventId}
Authorization: Bearer ACCESS_TOKEN
```

#### Implementation Example

```python
import httpx
from datetime import datetime

class GoogleCalendarClient:
    BASE_URL = "https://www.googleapis.com/calendar/v3"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def list_events(self, time_min: datetime = None, 
                          time_max: datetime = None):
        """Fetch events from Google Calendar."""
        async with httpx.AsyncClient() as client:
            params = {}
            if time_min:
                params["timeMin"] = time_min.isoformat()
            if time_max:
                params["timeMax"] = time_max.isoformat()
            
            response = await client.get(
                f"{self.BASE_URL}/calendars/primary/events",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def create_event(self, title: str, date: str, 
                           description: str = ""):
        """Create event in Google Calendar."""
        event = {
            "summary": title,
            "description": description,
            "start": {
                "date": date  # All-day event
            },
            "end": {
                "date": date  # All-day event
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/calendars/primary/events",
                headers=self.headers,
                json=event
            )
            response.raise_for_status()
            return response.json()
```

### Microsoft Graph API (Outlook)

#### Setup

1. Register app in Azure Portal
2. Configure API permissions (Calendars.ReadWrite)
3. Create client secret
4. Configure redirect URIs

#### API Endpoints

**List Events**:
```python
GET https://graph.microsoft.com/v1.0/me/events
Authorization: Bearer ACCESS_TOKEN

Query Parameters:
- $filter: startDateTime ge '2026-01-01T00:00:00Z'
- $top: Integer (pagination)
- $skip: Integer (pagination)
- $orderby: startDateTime
```

**Create Event**:
```python
POST https://graph.microsoft.com/v1.0/me/events
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json

Body:
{
  "subject": "Event Title",
  "body": {
    "contentType": "text",
    "content": "Event Description"
  },
  "start": {
    "dateTime": "2026-01-15T10:00:00",
    "timeZone": "Pacific Standard Time"
  },
  "end": {
    "dateTime": "2026-01-15T11:00:00",
    "timeZone": "Pacific Standard Time"
  }
}
```

### Synchronization Strategy

#### Bidirectional Sync

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   External   │         │     MCP      │         │   Database   │
│   Calendar   │◄───────►│    Server    │◄───────►│   Storage    │
│ (Google/MS)  │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
```

**Sync Process**:

1. **Initial Sync**: Fetch all events from external calendar
2. **Incremental Sync**: Use sync tokens to fetch only changes
3. **Conflict Resolution**: Last-write-wins or user-prompted
4. **Change Tracking**: Store modification timestamps

#### Sync Modes

**Pull Sync** (External → MCP):
```python
@mcp.tool()
async def sync_from_calendar(user_id: str, provider: str) -> str:
    """
    Pull events from external calendar to MCP server.
    
    Args:
        user_id: User identifier
        provider: "google" or "microsoft"
    
    Returns:
        Sync summary (events added, updated, deleted)
    """
    pass
```

**Push Sync** (MCP → External):
```python
@mcp.tool()
async def sync_to_calendar(user_id: str, provider: str) -> str:
    """
    Push events from MCP server to external calendar.
    
    Args:
        user_id: User identifier
        provider: "google" or "microsoft"
    
    Returns:
        Sync summary (events added, updated, deleted)
    """
    pass
```

**Automatic Sync**:
- Webhook notifications from providers
- Periodic polling (every 15 minutes)
- On-demand manual sync

---

## ICS File Support

### ICS Format Overview

ICS (iCalendar) is a standard format (RFC 5545) for calendar data exchange.

**Example ICS File**:
```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Calendar MCP Server//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:event-001@calendar-mcp-server
DTSTAMP:20260110T120000Z
DTSTART;VALUE=DATE:20260115
DTEND;VALUE=DATE:20260115
SUMMARY:Team Meeting
DESCRIPTION:Quarterly planning session
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
BEGIN:VEVENT
UID:event-002@calendar-mcp-server
DTSTAMP:20260110T120000Z
DTSTART;VALUE=DATE:20260220
DTEND;VALUE=DATE:20260220
SUMMARY:Dentist Appointment
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR
```

### Import ICS

#### Implementation

```python
from icalendar import Calendar
from datetime import datetime

@mcp.tool()
def import_ics(file_content: str) -> str:
    """
    Import events from ICS file content.
    
    Args:
        file_content: ICS file content as string
    
    Returns:
        Import summary (events imported, errors)
    
    Example ICS content:
        BEGIN:VCALENDAR
        VERSION:2.0
        BEGIN:VEVENT
        DTSTART:20260115
        SUMMARY:Meeting
        END:VEVENT
        END:VCALENDAR
    """
    try:
        cal = Calendar.from_ical(file_content)
        imported_count = 0
        errors = []
        
        for component in cal.walk():
            if component.name == "VEVENT":
                try:
                    title = str(component.get('summary'))
                    dt = component.get('dtstart').dt
                    
                    # Handle both date and datetime objects
                    if isinstance(dt, datetime):
                        date = dt.strftime("%Y-%m-%d")
                    else:
                        date = dt.isoformat()
                    
                    description = str(component.get('description', ''))
                    
                    # Add to events
                    events.append({
                        "title": title,
                        "date": date,
                        "description": description
                    })
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Error parsing event: {str(e)}")
        
        result = f"Imported {imported_count} events."
        if errors:
            result += f"\nErrors: {', '.join(errors)}"
        
        return result
        
    except Exception as e:
        return f"Failed to parse ICS file: {str(e)}"
```

#### Usage

```bash
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "import_ics",
    "input": {
      "file_content": "BEGIN:VCALENDAR\nVERSION:2.0\n..."
    }
  }'
```

### Export ICS

#### Implementation

```python
from icalendar import Calendar, Event
from datetime import datetime

@mcp.tool()
def export_ics() -> str:
    """
    Export all events to ICS format.
    
    Returns:
        ICS file content as string
    
    The returned content can be saved as .ics file
    and imported into any calendar application.
    """
    cal = Calendar()
    
    # Required calendar properties
    cal.add('prodid', '-//Calendar MCP Server//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    
    # Add each event
    for idx, event_data in enumerate(events):
        event = Event()
        
        # Generate unique ID
        event.add('uid', f"event-{idx:03d}@calendar-mcp-server")
        
        # Add timestamp
        event.add('dtstamp', datetime.now())
        
        # Add event details
        event.add('dtstart', datetime.strptime(event_data['date'], "%Y-%m-%d").date())
        event.add('dtend', datetime.strptime(event_data['date'], "%Y-%m-%d").date())
        event.add('summary', event_data['title'])
        
        if event_data['description']:
            event.add('description', event_data['description'])
        
        event.add('status', 'CONFIRMED')
        event.add('sequence', 0)
        
        cal.add_component(event)
    
    # Return ICS content
    return cal.to_ical().decode('utf-8')
```

#### Usage

```bash
# Export events
curl -X POST https://your-app.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "export_ics",
    "input": {}
  }' > my_calendar.ics

# Import into calendar app
open my_calendar.ics  # macOS
xdg-open my_calendar.ics  # Linux
```

### ICS as Fallback

When OAuth 2.0 authentication fails or API is unavailable:

1. **Export to ICS**: User downloads events as .ics file
2. **Manual Import**: User imports .ics into calendar app
3. **Import from ICS**: User uploads .ics to sync events back

**Advantages**:
- No authentication required
- Works offline
- Universal compatibility
- Simple implementation

**Limitations**:
- Manual process (not automatic)
- No real-time sync
- No conflict resolution
- One-way transfer per operation

---

## Architecture Design

### Enhanced System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
├────────────────────────────────────────────────────────────┤
│  • AI Assistants                                            │
│  • Web UI for OAuth flow                                    │
│  • File upload/download for ICS                             │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                      API Layer                              │
├────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐       │
│  │ MCP Handler │  │OAuth Handler│  │ ICS Handler  │       │
│  │ (existing)  │  │  (new)      │  │   (new)      │       │
│  └─────────────┘  └─────────────┘  └──────────────┘       │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                      │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐     │
│  │         MCP Tools (Enhanced)                      │     │
│  │  • Event CRUD operations                          │     │
│  │  • OAuth tools (new)                              │     │
│  │  • Sync tools (new)                               │     │
│  │  • ICS import/export (new)                        │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │         Calendar Clients (New)                    │     │
│  │  • GoogleCalendarClient                           │     │
│  │  • MicrosoftCalendarClient                        │     │
│  │  • ICSParser                                      │     │
│  └──────────────────────────────────────────────────┘     │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                    Data Layer (New)                         │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Database   │  │ OAuth Tokens │  │  Sync State  │    │
│  │   (Events)   │  │   Storage    │  │   Tracking   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                 External Services                           │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                       │
│  │   Google     │  │  Microsoft   │                       │
│  │   Calendar   │  │   Graph      │                       │
│  │     API      │  │     API      │                       │
│  └──────────────┘  └──────────────┘                       │
└────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Events table (replaces in-memory list)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    source VARCHAR(50) DEFAULT 'mcp',  -- 'mcp', 'google', 'microsoft', 'ics'
    external_id VARCHAR(255),  -- ID in external calendar
    external_etag VARCHAR(255),  -- For conflict detection
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    synced_at TIMESTAMP
);

-- OAuth tokens table
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    scope TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sync state table
CREATE TABLE sync_state (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,
    sync_token TEXT,  -- For incremental sync
    last_sync_at TIMESTAMP,
    next_sync_at TIMESTAMP,
    sync_status VARCHAR(50),  -- 'idle', 'syncing', 'error'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Indexes
CREATE INDEX idx_events_user_date ON events(user_id, date);
CREATE INDEX idx_events_external ON events(source, external_id);
CREATE INDEX idx_oauth_user_provider ON oauth_tokens(user_id, provider);
CREATE INDEX idx_sync_next_sync ON sync_state(next_sync_at);
```

---

## Implementation Roadmap

### Phase 1: OAuth 2.0 Foundation (2-3 weeks)

**Tasks**:
1. Set up Google Cloud project and OAuth credentials
2. Set up Azure AD app registration
3. Implement OAuth endpoints (initiate, callback, refresh)
4. Create token storage (database table)
5. Add token encryption
6. Test OAuth flow end-to-end

**Deliverables**:
- Working OAuth login for Google and Microsoft
- Secure token storage
- Token refresh mechanism

### Phase 2: Calendar API Integration (3-4 weeks)

**Tasks**:
1. Implement GoogleCalendarClient class
2. Implement MicrosoftCalendarClient class
3. Create unified calendar interface
4. Add API error handling
5. Implement rate limiting
6. Test API operations

**Deliverables**:
- List events from external calendars
- Create/update/delete events in external calendars
- Error handling and retry logic

### Phase 3: Synchronization (2-3 weeks)

**Tasks**:
1. Design sync algorithm
2. Implement pull sync (external → MCP)
3. Implement push sync (MCP → external)
4. Add conflict resolution
5. Implement sync tokens for incremental sync
6. Add sync scheduling

**Deliverables**:
- Bidirectional sync working
- Conflict resolution strategy
- Periodic background sync

### Phase 4: ICS Support (1-2 weeks)

**Tasks**:
1. Add icalendar library dependency
2. Implement ICS import tool
3. Implement ICS export tool
4. Add file upload endpoint
5. Test ICS compatibility with major calendar apps

**Deliverables**:
- Import events from ICS files
- Export events to ICS format
- Compatibility with common calendar apps

### Phase 5: Database Migration (1-2 weeks)

**Tasks**:
1. Choose database (PostgreSQL recommended)
2. Set up database on Vercel (or external service)
3. Create schema and migrations
4. Migrate from in-memory to database storage
5. Update all tools to use database

**Deliverables**:
- Persistent event storage
- Database migrations
- Backward compatibility

### Phase 6: Testing & Documentation (1-2 weeks)

**Tasks**:
1. Write comprehensive unit tests
2. Write integration tests
3. Write end-to-end tests
4. Update all documentation
5. Create user guides
6. Create developer guides

**Deliverables**:
- >80% test coverage
- Complete documentation
- User and developer guides

---

## Security Considerations

### OAuth Security

**Token Security**:
- Encrypt tokens at rest using AES-256
- Use environment variables for encryption keys
- Rotate encryption keys periodically
- Never log tokens

**CSRF Protection**:
- Generate random state parameter (256-bit)
- Store state in secure session or database
- Validate state on callback
- Expire state after 10 minutes

**Authorization**:
- Request minimal OAuth scopes
- Implement scope verification
- Allow users to revoke tokens
- Audit access logs

### API Security

**Rate Limiting**:
- Implement per-user rate limits
- Use exponential backoff for retries
- Handle 429 responses gracefully
- Cache responses when possible

**Input Validation**:
- Validate all user inputs
- Sanitize HTML in descriptions
- Validate date formats
- Limit string lengths

**Data Privacy**:
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Implement data retention policies
- Comply with GDPR/CCPA

### Webhook Security

**Verification**:
- Validate webhook signatures
- Use HMAC-SHA256 for signing
- Verify timestamp to prevent replay attacks
- Whitelist provider IP addresses

---

## Dependencies

### New Python Packages

```toml
[project]
dependencies = [
    "fastmcp>=0.1.0",
    "httpx>=0.25.0",          # HTTP client for API calls
    "icalendar>=5.0.0",       # ICS parsing and generation
    "cryptography>=41.0.0",   # Token encryption
    "python-jose>=3.3.0",     # JWT handling
    "asyncpg>=0.29.0",        # PostgreSQL async driver
    "pydantic>=2.5.0",        # Data validation
    "python-dotenv>=1.0.0",   # Environment variables
]
```

### External Services

**Required**:
- Database (PostgreSQL recommended)
- Google Cloud project with Calendar API
- Azure AD app registration

**Optional**:
- Redis for caching
- Background job queue (Celery, RQ)
- Monitoring service (Sentry, DataDog)

---

## Testing Strategy

### Unit Tests

```python
# Test OAuth token management
def test_oauth_token_encryption():
    token = "secret-access-token"
    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)
    assert decrypted == token

# Test ICS import
def test_import_ics():
    ics_content = """
    BEGIN:VCALENDAR
    VERSION:2.0
    BEGIN:VEVENT
    DTSTART:20260115
    SUMMARY:Test Event
    END:VEVENT
    END:VCALENDAR
    """
    result = import_ics(ics_content)
    assert "Imported 1 events" in result
```

### Integration Tests

```python
# Test Google Calendar sync
async def test_google_calendar_sync():
    # Mock OAuth token
    token = create_test_token("google")
    
    # Create test event in MCP
    add_event("Test", "2026-01-15", "Test event")
    
    # Sync to Google Calendar
    result = await sync_to_calendar("test-user", "google")
    
    # Verify event exists in Google Calendar
    events = await google_client.list_events()
    assert any(e['summary'] == "Test" for e in events['items'])
```

### End-to-End Tests

```python
# Test full OAuth flow
async def test_oauth_flow():
    # Step 1: Initiate OAuth
    auth_url = initiate_oauth("google")
    assert "accounts.google.com" in auth_url
    
    # Step 2: Simulate callback with code
    result = await oauth_callback(code="test-code", state="test-state")
    assert "success" in result.lower()
    
    # Step 3: Verify token stored
    token = get_token("test-user", "google")
    assert token is not None
```

---

## Monitoring and Observability

### Metrics

**OAuth Metrics**:
- OAuth attempts
- OAuth success rate
- Token refresh rate
- Token expiration rate

**Sync Metrics**:
- Sync frequency
- Sync duration
- Events synced per operation
- Sync errors and failures

**API Metrics**:
- API call rate (per provider)
- API response time
- API error rate
- Rate limit hits

### Logging

**Structured Logging**:
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_sync_event(user_id, provider, action, details):
    logger.info(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "event_type": "sync",
        "user_id": user_id,
        "provider": provider,
        "action": action,
        "details": details
    }))
```

### Alerts

**Critical Alerts**:
- OAuth service down
- Database connection failures
- High error rate (>5%)
- Sync failures for >1 hour

**Warning Alerts**:
- Token refresh failures
- API rate limit approaching
- Slow sync performance
- Database query slow

---

## Conclusion

This calendar synchronization feature will transform the Calendar MCP Server from a simple in-memory event store to a comprehensive calendar management system with enterprise-grade authentication, external calendar integration, and flexible import/export capabilities.

The phased implementation approach ensures each component is thoroughly tested before moving to the next, minimizing risks and allowing for iterative improvements based on user feedback.

For questions or contributions, see [CONTRIBUTING.md](CONTRIBUTING.md).
