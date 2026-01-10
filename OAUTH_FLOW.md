# OAuth 2.0 Authentication Flow

## Overview

This document describes the OAuth 2.0 authentication flow implemented in the calendar-mcp-server.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interaction Flow                        │
└─────────────────────────────────────────────────────────────────┘

1. User initiates connection
   │
   ↓
2. System calls: get_consent_prompt()
   │
   ↓ Returns consent message
   │
   ┌──────────────────────────────────────────────────────┐
   │ "This application would like to access your Google   │
   │  Calendar and Gmail account.                         │
   │                                                       │
   │  Permissions requested:                              │
   │  - Read and manage your calendar events              │
   │  - Read your email messages                          │
   │  - Access your basic profile information             │
   │                                                       │
   │  Do you accept the connection to your email          │
   │  account and calendar?"                              │
   └──────────────────────────────────────────────────────┘
   │
   ↓ User accepts
   │
3. System calls: start_oauth_flow()
   │
   ↓ Returns Google authorization URL
   │
   ┌──────────────────────────────────────────────────────┐
   │ "Please visit the following URL to authorize         │
   │  access:                                             │
   │                                                       │
   │  https://accounts.google.com/o/oauth2/auth?...       │
   │                                                       │
   │  After authorizing, you will receive a code.         │
   │  Use the 'complete_oauth_flow' tool with that code." │
   └──────────────────────────────────────────────────────┘
   │
   ↓ User visits URL and grants permissions
   │
   ↓ Google provides authorization code
   │
4. System calls: complete_oauth_flow(authorization_code)
   │
   ↓ Exchanges code for tokens
   │
   ↓ Fetches user profile (including first name)
   │
   ↓ Stores credentials in token.json
   │
   ↓ Returns welcome message
   │
   ┌──────────────────────────────────────────────────────┐
   │ "Welcome, [FirstName]! You are now connected to      │
   │  your calendar and email."                           │
   └──────────────────────────────────────────────────────┘
   │
   ↓
5. User is authenticated and can use calendar tools
```

## MCP Tools

### Authentication Tools

1. **get_consent_prompt()**
   - Purpose: Display permission request to user
   - Returns: Consent message explaining what permissions are needed
   - Use: Call before starting OAuth flow

2. **start_oauth_flow()**
   - Purpose: Initiate OAuth 2.0 authentication
   - Returns: Google authorization URL
   - Use: Call after user accepts consent

3. **complete_oauth_flow(authorization_code: str)**
   - Purpose: Complete authentication with authorization code
   - Parameters: 
     - `authorization_code`: Code received from Google after authorization
   - Returns: Welcome message with user's first name
   - Use: Call after user authorizes access on Google's consent screen

4. **get_welcome_message()**
   - Purpose: Get welcome message with user's first name
   - Returns: Personalized welcome message if authenticated, otherwise authentication prompt
   - Use: Call anytime to check authentication and get welcome message

5. **check_authentication_status()**
   - Purpose: Check current authentication status
   - Returns: Authentication status and user name if authenticated
   - Use: Call to verify if user is authenticated

### Calendar Management Tools

These tools remain unchanged from the original implementation:

- **add_event(title, date, description)**: Add a calendar event
- **view_events()**: View all scheduled events
- **delete_event(title)**: Delete an event by title
- **summarize_events()**: Get a summary of upcoming events

## Security Features

1. **Credential Storage**
   - OAuth credentials stored in `token.json` (gitignored)
   - Credentials file `credentials.json` excluded from version control
   - Tokens automatically refreshed when expired

2. **Scopes**
   - Google Calendar API: Full access to calendar
   - Gmail API: Read-only access to email
   - OAuth2 API: Basic profile information (name)

3. **Error Handling**
   - Graceful handling of missing credentials file
   - Silent error handling for failed API calls
   - Clear error messages returned to user

## Setup Requirements

1. **Google Cloud Console**
   - Create OAuth 2.0 credentials
   - Enable Google Calendar API
   - Enable Gmail API
   - Enable OAuth2 API

2. **credentials.json**
   - Download from Google Cloud Console
   - Place in project root
   - See `credentials.json.example` for format

3. **Dependencies**
   - google-auth
   - google-auth-oauthlib
   - google-api-python-client
   - mcp

## User Experience

The authentication flow provides:
- ✅ Clear consent prompt before OAuth flow
- ✅ Explicit permission listing
- ✅ Personalized welcome message with first name
- ✅ Persistent authentication (saved tokens)
- ✅ Automatic token refresh
- ✅ User-friendly error messages
