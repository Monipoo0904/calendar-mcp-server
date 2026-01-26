# Vercel Event Calendar (Demo)

This repository is a Vercel-compatible demo of an MCP-based Event Calendar server.

- API endpoint: `/api/mcp`
- Frontend: `public/index.html` (simple chat UI)

Quick local test

1. Install dev deps for local testing:

```bash
python -m pip install -r requirements.txt
```

2. Run the test harness:

```bash
python test_local.py
```

Deploy to Vercel

1. Ensure `vercel` CLI is installed and logged in.
2. Run `vercel deploy` and follow prompts.
3. Your serverless endpoint will be available at `https://<project>.vercel.app/api/mcp`.

Notes

- Vercel serverless functions are stateless — events are stored in-memory and **will reset** frequently.
- The demo includes a **conversational** `handle_message` tool that accepts both terse commands and natural language. Examples:
  - `list` or `list events` → lists all events
  - `list events on 2026-01-01` or `What's on 2026-01-01?` → lists events for that date
  - `summarize` / `summary` / `what's coming up` → summary of upcoming events
  - `add:Title|YYYY-MM-DD|Desc` (shorthand, still supported)
  - `Add Birthday on 2026-02-01 about cake` → conversational add
  - `Create Meeting on 2026-03-03` → conversational add
  - `Add Meeting tomorrow` → supports `today` and `tomorrow`
  - `delete:Title` or `delete Meeting` or `remove Meeting` → deletes by title

  If a message isn't understood, the handler returns a short help text with examples.

Frontend improvements:

- Chat UI now supports typing indicator, timestamps, avatars, copy-to-clipboard buttons, Shift+Enter for newlines, Enter to send, and conversation persistence in `localStorage`. The composer shows a spinner while the backend responds and disables input until a reply is received.

## Development & Contributing

If you plan to edit or extend this project, see `DEVELOPING.md` for a detailed developer guide (setup, editing the frontend and backend, testing, and deployment to Vercel).


Contributions should follow the branch-per-feature workflow and include clear commit messages (use prefixes like `feat:`, `fix:`, `style:`, or `docs:`). Please open a PR for review and testing before merging to the main branch.

## Editing Test Sign-in Buttons

These buttons in the UI are currently wired as local test buttons (they do not perform OAuth). To edit them or change their behavior:

- File: [public/index.html](public/index.html#L1)
  - Buttons: `#signinGoogle` and `#signinMicrosoft` are in the header under `.auth-controls`.
  - Change the button label or markup directly in this file.

- File: [public/script.js](public/script.js#L1)
  - Test handler: `testSignIn(provider)` simulates a sign-in. Edit or replace this function to change test behavior.
  - To restore real OAuth behavior, replace the click handlers with the `startOauth(provider)` calls:

```js
// example: restore OAuth start
document.getElementById('signinGoogle').addEventListener('click', () => startOauth('google'));
document.getElementById('signinMicrosoft').addEventListener('click', () => startOauth('microsoft'));
```

- Quick test locally:

```bash
# start the local test harness
python -m pip install -r requirements.txt
python test_local.py

# open the app at http://localhost:3000 (or the port printed by the harness)
```

- Commit & push changes:

```bash
git add public/index.html public/script.js README.md
git commit -m "chore: add test sign-in buttons and docs"
git push origin HEAD:copilot/integrate-oauth-email-login
```

These notes keep the UI test-friendly and make it easy to rewire the buttons for a real OAuth flow later.
