# Developing Event Calendar (Developer Notes)

This document explains how the project is structured and how to edit, test, and deploy it.

## Project overview
- Backend: FastMCP + FastAPI (see `main.py`). MCP tools (functions) are added using the `@mcp.tool()` decorator and are exposed via the `/api/mcp` endpoint.
- Serverless wrapper: `api/mcp.py` contains a Vercel-compatible handler used for serverless deployments (supports preflight CORS and unwraps common response shapes).
- Frontend: Static files in `public/`:
  - `index.html` — top-level markup and layout
  - `style.css` — all styles (theme variables live here)
  - `script.js` — chat UI behavior, localStorage, and API calls

> Note: Events are currently stored in-memory on the server (`events` list in `main.py`) and will reset on cold starts or redeploys. For persistent data, add a database and persist events.

---

## Local development

Prerequisites
- Python 3.12 (see `.python-version`)
- `pip` and optionally `venv` or other virtual environment tooling
- (Optional) Vercel CLI for local serverless testing and deployment

Quick start
1. Create and activate a virtualenv (macOS example):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. Run the test harness (calls the serverless handler directly):

```bash
python test_local.py
```

3. Run the app locally (FastAPI + uvicorn):

```bash
python -m uvicorn main:app --reload
# Open http://127.0.0.1:8000
```

4. To experiment with the serverless wrapper locally (`api/mcp.py`) you can use `vercel dev` (requires Vercel CLI) or call `handler()` directly in an async test harness (see `test_local.py`).

---

## Editing the frontend

Files of interest:
- `public/index.html` — edit structure, add UI elements, ARIA roles
- `public/style.css` — theme variables at the top using `:root` and `[data-theme="light"]` overrides; change `--bg`, `--panel-bg`, `--text`, and `--muted` for global color changes.
- `public/script.js` — key functions:
  - `renderMessage(msg)` — how messages are rendered in the DOM (avatar, bubble, meta)
  - `addLocalMessage(text, who)` — adds messages to local `chat[]` and persists to `localStorage` (`chat_messages` key)
  - `showTyping()` / `removeTyping()` — typing indicator
  - `setFetching(state)` — disables composer and shows spinner while waiting for a reply
  - Theme helpers: `setTheme(t)` and `loadTheme()` manage `data-theme` attribute

Developer notes — recent features and where to edit
- Time parsing and conversational adds: see `main.py`:
  - `handle_message(message)` implements the conversational parsing logic. Date detection and normalization happen in `find_date_in_msg()` and `parse_date_token()`; time normalization is in `parse_time_token()`.
  - `add_event(title, date, description)` now accepts date+time formats and stores events as either `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`.
- .ics export: the `GET /export.ics` route is defined in `main.py` and serializes the in-memory `events` list to a downloadable iCalendar file. Timed events are emitted with a `DTSTART` timestamp; date-only events are exported as `DTSTART;VALUE=DATE`.
- Project planning + LLM: 
  - **Server-side**: `research_and_breakdown(goal, deadline)` tool in `main.py` calls OpenRouter API when `LLM_API_KEY` environment variable is set. Falls back to heuristic plan generation if LLM is unavailable.
  - **Client-side flow**: `public/script.js` implements the planning UI flow using browser prompts. When user types "plan" or clicks "Start Project", it prompts for goal, deadline (YYYY-MM-DD), then calls the `research_and_breakdown` tool via `/api/mcp`. The plan is displayed with a "Create tasks from plan" button that calls the `create_tasks` tool.
  - **Create button rendering (important for edits)**:
    - The plan action button is injected in `submitProjectGoal()` as a full chat message element (`<div class="message bot">`) containing avatar + bubble + button.
    - Keep the button query scoped to that injected block (e.g., `actionEl.querySelector('.create-tasks-btn')`) so handlers are attached reliably.
    - If the button disappears after changes, verify you are appending the full action element to `#messages` and that no later code removes/replaces it.
  - **Cadence + reminders flow**:
    - After clicking "Create tasks from plan", client prompts for cadence and whether reminders should be created.
    - Task creation uses server tool `create_tasks`; reminder cadence uses `set_recurrence` per milestone.
    - If you rename cadence values, keep them aligned with accepted `set_recurrence` frequency keys in `main.py`.
  - **Prompt trigger dependency**:
    - The quick "Start Project" button is text-triggered by the bot phrase `What would you like to accomplish?` in `interceptGoalPrompt()`.
    - If you change that phrase, also update the regex trigger to avoid breaking the initial quick-start button.
  - **Important**: Planning flow is entirely client-side to avoid state issues in serverless deployments. The server only provides stateless tools (`research_and_breakdown`, `create_tasks`).
  - **Environment variable**: Set `LLM_API_KEY` in Vercel project settings for LLM-powered planning. Otherwise, heuristic plans are generated.
- UI examples and guidance: update `public/index.html` (composer tooltip, `composerHelp`) and `public/script.js` (welcome bot message) to change the examples or instructions shown to users.
- Styling: `public/style.css` contains variables at the top (`:root`) and the `auth-button` class used by the Connect and Export buttons.

Suggested edit flow
1. Update parsing logic in `main.py` and write unit tests for `find_date_in_msg()` and `parse_time_token()`.
2. Update UI examples in `public/index.html` and `public/script.js` to reflect new behaviors.
3. Adjust style in `public/style.css` if you change control sizing or spacing.
4. If adding timezone or end-time support, update the `.ics` exporter and document timezone expectations in the README.

Notes about deployment
- `api/mcp.py` is a serverless handler continuity helper — use it if deploying to Vercel. If you introduce OAuth flows, ensure the provider redirect URIs match your deployment host and secure client credentials (do not commit them to the repo).
- LLM settings:
  - `LLM_API_KEY`: OpenRouter API key.
  - `OPENROUTER_MODEL`: optional override for the model name (default: `google/gemini-3-flash-preview`).

Tips:
- Avatars: change the emoji strings in `renderMessage` and `showTyping`.
- Adding UI elements: update the HTML markup and corresponding CSS classes; keep `messages` container as `role="log" aria-live="polite"` for screen readers.
- Persisted state: `localStorage` is used for chat persistence — clear it to reset saved conversations.

---

## Editing the backend

- `main.py` contains the FastMCP instance and FastAPI app.
- `handle_message` is implemented as a conversational parser to allow more natural phrases (see the function docstring in `main.py` for details).
- To add or tweak conversational patterns:
  - Edit `handle_message` in `main.py`. The function uses a small set of regexes to interpret common forms (add/create/schedule with `on YYYY-MM-DD`, `today`, `tomorrow`; delete/remove/cancel; list queries with optional dates; summarize variants).
  - Keep parsing simple and test with `curl` or `test_local.py` after changes. Aim for clarity and predictable fallbacks — when in doubt return a short help message rather than guessing user intent.

- To add a new tool:
  - Decorate the function with `@mcp.tool()` (or `@mcp.prompt()` for prompt-style wrappers)
  - Keep functions simple and return serializable strings or objects
  - Example:

```python
@mcp.tool()
def my_tool(foo: str) -> str:
    return f"You passed {foo}"
```

- The FastAPI endpoint `/api/mcp` expects JSON: `{"tool":"tool_name","input":{...}}`.
- Test tools via `curl` or http clients. Example:

```bash
curl -s -X POST http://127.0.0.1:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool":"handle_message","input":{"message":"list"}}'
```

- `api/mcp.py` is a convenience wrapper for serverless deployments; it supports both frameworks that pass `request.json()` as a coroutine and frameworks that pass a dict-like `request` object.

---

## Deployment (Vercel)

- The project contains `vercel.json` with an `installCommand` (`pip install -r requirements.txt`) and a redirect from `/` to `/index.html`.
- To deploy:
  - Install and login with `vercel` CLI
  - `vercel deploy` and follow prompts
  - Note: function runtime pinning caused validation issues before; prefer letting Vercel auto-detect the runtime or use an accepted `functions` configuration.

---

## Testing & QA

- Basic tests: `test_local.py` (sanity test calls the handler directly)
- Manual API checks: use `curl` or `httpie` against `/api/mcp`
- Front-end checks: run `uvicorn` and open the page; watch console logs in the browser devtools
- Accessibility: check `aria-live` announcements, contrast (Lighthouse / axe), keyboard focus states

---

## Style, linting, and formatting (recommended)
- Add `black`, `ruff`, and `pre-commit` for consistent formatting and linting
- Example install:

```bash
python -m pip install black ruff pre-commit
pre-commit install
```

---

## Git workflow
- Use feature branches (e.g., `feature/chat-ui`, `fix/light-theme-contrast`)
- Commit messages: short prefix (`feat:`, `fix:`, `style:`, `docs:`) followed by a concise description
- Open PRs for changes and request at least one reviewer

---

## Where to look when things break
- Server logs (uvicorn output) for tracebacks
- Browser console/network tab for failed fetches to `/api/mcp`
- `vercel logs <deployment>` for serverless runtime issues

---

## Contact / Maintainers
- Repo owner: (replace with actual maintainer contact info)

---

If you'd like, I can also add a `CONTRIBUTING.md` or a simple `Makefile` with common dev tasks (install, run, test, lint). Let me know which extras you want.
