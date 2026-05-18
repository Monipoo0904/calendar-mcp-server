# Vercel Event Calendar (Demo)

This repository is a Vercel-compatible demo of an MCP-based Event Calendar server.

- API endpoint: `/api/mcp`
- Frontend: `public/index.html` (conversational chat UI)

## How the Chat Works

The chat uses a **conversational, intent-aware** flow:

### Chat Process Flow

1. **User enters a message** in the composer
   - Press `Enter` to send, or `Shift+Enter` for a newline
   - Message is added to the chat and displayed immediately as a user message

2. **Intent detection** — the frontend checks if the message looks like a **student lesson planning** request
   - If yes → special student planning flow (multi-step, with student selection and personalized goals)
   - If no → standard **`handle_message`** tool flow (see below)

3. **Standard `handle_message` flow** (for calendar events, queries, and general commands)
   - Sends the message to the backend tool: `POST /api/mcp` with `{ tool: 'handle_message', input: { message } }`
   - Shows a typing indicator while waiting
   - Backend parses the message with natural language support
   - Backend returns a result (e.g., event added, list of events, error)
   - Result is displayed as a bot message in the chat
   - Input is re-enabled

4. **Recurrence prompts** — after adding an event, the UI may show recurrence options
   - User selects a recurrence type (daily, weekly, custom, etc.)
   - Sends `set_recurrence` tool call with the selected frequency
   - Recurrence is stored with the event (in-memory; resets on redeploy)

5. **Export .ics** — after creating events or a plan
   - An export button is offered in the chat
   - Click to download a standard iCalendar file (`.ics`)
   - Optional: export by student or scope (requires `personalized_lesson_plans` tool)

### Supported Commands & Natural Language

The `handle_message` tool understands both **terse commands** and **natural language**:

- **List events**
  - `list` / `list events` → all events
  - `list events on 2026-01-01` / `What's on 2026-01-01?` → events for that date
  - Shorthand: `list:2026-01-01`

- **Add events** (supports times)
  - `Add Birthday on 2026-02-01` → all-day event
  - `Add Meeting March 5 about planning` → natural language parsing
  - `Add Lunch tomorrow` → recognizes `today` / `tomorrow`
  - `Add Meeting on 2026-02-01 at 14:30` → time-specific event
  - Shorthand: `add:Title|YYYY-MM-DD|Desc` or `add:Title|YYYY-MM-DD HH:MM|Desc`
  - Time ranges: `Add Meeting on 2026-02-01 from 3pm to 5pm` → sets both start and end times

- **Delete events**
  - `delete Meeting` / `remove Birthday` → by title
  - Shorthand: `delete:Title`

- **Summarize**
  - `summarize` / `summary` / `what's coming up` → upcoming events overview

- **Help**
  - If a message isn't understood, the server returns a short help text with examples

### Student Lesson Planning Flow

If the chat detects a message like *"create lesson plans for students"*, it triggers the **student planning flow**:

1. **Fetch available students** from the configured webhook (`STUDENT_SKILLS_WEBHOOK_URL`)
2. **Multi-select interface** — user picks which students to plan for
3. **Personalized goals** — for each student, user provides a custom objective
4. **Generate plans** — backend calls `personalized_lesson_plans` tool
5. **Create calendar tasks** — user is offered per-student calendar creation
6. **Export as .ics** — option to export all selected students' milestones as individual `.ics` files

## Local Testing & Development

1. Install dev dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Run the local test harness:

```bash
python test_local.py
```

3. Open your browser to the printed URL (usually `http://localhost:3000`)

4. Start adding events! Try:
   - `Add Birthday on 2026-02-01`
   - `Add Meeting March 5 about planning`
   - `Add Lunch tomorrow`
   - `list` or `what's coming up`
   - Short form: `add:Meeting|2026-03-01|with team`

### Deploy to Vercel

1. Ensure `vercel` CLI is installed and logged in: `npm install -g vercel`
2. Run `vercel deploy` and follow prompts
3. Your endpoint will be at `https://<project>.vercel.app/api/mcp`

### Microsoft Calendar OAuth (Optional)

The demo includes Microsoft Outlook integration. To enable it:

1. Set environment variables:
   - `MS_CLIENT_ID` — Azure AD application client ID
   - `MS_CLIENT_SECRET` — Azure AD application secret
   - `MS_TENANT_ID` (optional, default: `common`)
   - `MS_REDIRECT_URI` (optional, default: `<base>/api/oauth/microsoft/callback`)

2. The "Connect to Microsoft Calendar" button will:
   - Call `GET /api/oauth/microsoft/start` (builds auth URL)
   - Redirect user to Microsoft login
   - Callback at `GET /api/oauth/microsoft/callback` exchanges code for token
   - Frontend displays `Connected: <name>` in the header

3. If environment variables are not configured, the button falls back to a dev redirect page (`redirect_microsoft.html`)

## Notes

- Vercel serverless functions are stateless — events are stored in-memory and **will reset** frequently
- The demo includes a **conversational** `handle_message` tool (see "Supported Commands & Natural Language" above)
- All MCP tools are exposed via `POST /api/mcp` with shape: `{ tool: 'tool_name', input: { ... } }`
- Chat messages persist in browser **localStorage** (key: `chat_messages`), so conversations survive page reloads

## Backend Tools

The MCP server exposes these main tools (called from the chat):

- **`handle_message`** — parses a user text message and routes to appropriate action (add event, list, delete, summarize, etc.)
- **`add_event`** — creates a calendar event (called internally by `handle_message`)
- **`set_recurrence`** — sets a recurrence pattern on an existing event (called after user clicks recurrence option)
- **`create_tasks`** — creates a multi-step plan as calendar milestones (called during project planning flow)
- **`personalized_lesson_plans`** — fetches from webhook and generates student-specific lesson plans
- **`export_ics`** — generates a `.ics` (iCalendar) file for download

See [main.py](main.py) for tool implementations and [api/mcp.py](api/mcp.py) for the serverless FastAPI wrapper.

## Editor Guide: Where to Edit Behavior

### Chat Parser & Event Logic

- **File**: [main.py](main.py)
  - **Conversational parsing**: `handle_message(message)` — natural language parsing logic, date/time detection
  - **Date detection**: `find_date_in_msg(msg)` — extracts dates like "tomorrow", "March 5", "2026-01-01"
  - **Time normalization**: `parse_time_token(token)` — parses times like "3pm", "14:30", "3pm-5pm"
  - **Event storage**: `add_event(title, date, description)` — validation and in-memory storage
  - **Recurrence logic**: `set_recurrence(title, frequency, interval)` — computes next recurrence dates

### Frontend Chat UI

- **File**: [public/script.js](public/script.js)
  - **Chat input handler**: `form.addEventListener('submit', ...)` (line 912) — intercepts form submission
  - **Intent detection**: `looksLikeStudentPlanRequest(text)` — regex check for student planning keywords
  - **Message rendering**: `renderMessage(msg)` — DOM creation for chat bubbles, timestamps, copy buttons
  - **Message persistence**: `load()` and `save()` — localStorage read/write
  - **Typing indicator**: `showTyping()` / `removeTyping()` — animated dots while fetching
  - **Recurrence UI**: `showRecurrencePrompt(title)` — button grid for recurrence choices

- **File**: [public/index.html](public/index.html)
  - **Chat layout**: `#messages` (role="log", aria-live="polite") — main message container
  - **Input composer**: `#input` (textarea), `#form` (submit), `#sendBtn` — message input and send button
  - **Help text**: bottom `p.help` paragraph — shows example commands to users

### Making Common Changes

1. **Edit example commands shown to users**
   - File: [public/index.html](public/index.html) — edit the `p.help` paragraph at bottom
   - File: [public/script.js](public/script.js) — edit the welcome message in `addLocalMessage(...)`

2. **Add a new recurrence type**
   - File: [public/script.js](public/script.js#L950) — add a `<button>` in `showRecurrencePrompt()`
   - File: [main.py](main.py) — add logic to `set_recurrence()` to handle the new frequency

3. **Customize the chat bubble appearance**
   - File: [public/style.css](public/style.css#L54-L58) — avatar colors and styles
   - File: [public/script.js](public/script.js#L760) — renderMessage() HTML structure

4. **Add a new intent to the chat**
   - File: [public/script.js](public/script.js#L912) — add condition after `const text = input.value.trim()`
   - File: [main.py](main.py) — add new tool and call it from the form handler

### Advanced: Replacing In-Memory Storage

Currently, all events are stored in a Python list in `main.py`. For production:

- Replace `events = []` with a database connection (e.g., PostgreSQL, Redis, DynamoDB)
- Modify `add_event()`, `get_events()`, `delete_event()`, `set_recurrence()` to use DB operations
- For Vercel, consider AWS DynamoDB or a managed database service

## Development & Contributing

If you plan to edit or extend this project, see `DEVELOPING.md` for a detailed developer guide (setup, editing the frontend and backend, testing, and deployment to Vercel).


Contributions should follow the branch-per-feature workflow and include clear commit messages (use prefixes like `feat:`, `fix:`, `style:`, or `docs:`). Please open a PR for review and testing before merging to the main branch.

## Editing & Customization

### Theme, Colors & Avatars

- **Theme / colors**: color variables live at the top of [public/style.css](public/style.css#L1). Change `--bg`, `--panel-bg`, `--text`, `--accent`, and `--send` to tune the palette.
- **Avatars**: avatar styles are in [public/style.css](public/style.css#L1) under `.message .avatar`. User avatar is 🌞, bot avatar is ⭐. Edit `color`, `background`, or `border-radius` to customize.

### Buttons (UI)

- **Sign-in / Connect buttons**: in [public/index.html](public/index.html#L1), the header contains authentication buttons:
  - `#signinGoogle` and `#signinMicrosoft` (currently test buttons)
  - Change label text or classes directly in HTML
  - To restore real OAuth, change click handlers in [public/script.js](public/script.js) to call `startOauth(provider)`

### Redirect Pages (OAuth Fallback)

- **Microsoft redirect**: [public/redirect_microsoft.html](public/redirect_microsoft.html) — dev fallback when OAuth is not configured
- **Google redirect**: [public/redirect_google.html](public/redirect_google.html) — similar fallback
- Edit the URL or meta-refresh delay as needed
