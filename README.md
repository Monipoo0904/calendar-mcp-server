# Event Calendar MCP Server

An MCP (Model Context Protocol) server for managing calendar events with Google Calendar and Gmail integration.

## Features

- OAuth 2.0 authentication with Google
- User welcome message with first name
- Permission prompts for calendar and email access
- Add, view, and delete calendar events
- Event summaries

## Setup

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Calendar API
   - Gmail API
   - Google OAuth2 API
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Configure the OAuth consent screen
6. Choose "Desktop app" as the application type
7. Download the credentials JSON file and save it as `credentials.json` in the project root

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

or with uv:

```bash
uv pip install -e .
```

### 3. Authentication Flow

The application uses OAuth 2.0 for authentication. Users will:

1. See a consent prompt asking for permission to access calendar and email
2. Be redirected to Google's authorization page
3. Grant permissions
4. Receive a welcome message with their first name

## Usage

### Authentication Tools

- `get_consent_prompt()` - Display the permission request message
- `start_oauth_flow()` - Start OAuth authentication and get authorization URL
- `complete_oauth_flow(authorization_code)` - Complete authentication with the received code
- `get_welcome_message()` - Get welcome message with user's first name
- `check_authentication_status()` - Check current authentication status

### Calendar Management Tools

- `add_event(title, date, description)` - Add a new calendar event
- `view_events()` - View all scheduled events
- `delete_event(title)` - Delete an event by title
- `summarize_events()` - Get a summary of upcoming events

## Running the Server

```bash
python main.py
```

For local testing:

```bash
python test_local.py
```

## Deployment

This server is designed to be deployed on Vercel. The `vercel.json` configuration is already set up.

## Security

- OAuth tokens are stored locally in `token.json` (gitignored)
- Never commit `credentials.json` or `token.json` to version control
- Credentials are automatically refreshed when expired
