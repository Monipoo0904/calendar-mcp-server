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

## Editing & Customization

- **Buttons (UI)**: edit the sign-in buttons in [public/index.html](public/index.html#L1). The two buttons are `#signinGoogle` and `#signinMicrosoft` inside the header's `.auth-controls` element. Change label text or classes there.

- **Button behavior (client-side)**: modify the click handlers and simulated responses in [public/script.js](public/script.js#L1). The `testSignIn(provider)` function (or `startOauth(provider)` if you restore OAuth) controls what happens on click. To restore real OAuth, wire the handlers to `startOauth('google')` / `startOauth('microsoft')`.

- **Redirect pages**: the small landing pages are [public/redirect_google.html](public/redirect_google.html) and [public/redirect_microsoft.html](public/redirect_microsoft.html). They perform a 1s meta-refresh to the external site; edit the copy or destination URL inside these files if desired.

- **Theme / colors**: color variables live at the top of [public/style.css](public/style.css#L1). Change `--bg`, `--panel-bg`, `--text`, `--accent`, and `--send` to tune the palette. The default theme is set in [public/script.js](public/script.js#L1) (`loadTheme()` uses localStorage key `ui_theme`). To default to dark again, set the default in `loadTheme()`.

- **Avatars & icons**: avatar styles are in [public/style.css](public/style.css#L1) under `.message .avatar`. Update `color`, `background`, or border-radius to change their appearance. Emoji avatars are rendered as text; set `color` for contrast.

- **Backend tools**: server-side MCP tools live in `api/mcp.py` and the message handler is available as the `handle_message` tool. If you add new UI controls that call backend tools, ensure the POST body matches the MCP shape used by the frontend (`{ tool: 'tool_name', input: { ... } }`).

- **Local testing**: run the quick test harness:

```bash
python -m pip install -r requirements.txt
python test_local.py
# then open http://localhost:3000 (or the printed URL)
```

- **Committing & pushing**: recommended commit pattern:

```bash
git checkout -b feat/your-feature
git add <files>
git commit -m "feat: brief description"
git push origin HEAD:copilot/integrate-oauth-email-login
```

- **Restoring OAuth**: if you want to re-enable OAuth flows, revert the test handlers in `public/script.js` to call `startOauth(provider)` and re-enable server-side OAuth code in `oauth_manager.py` and any `api/oauth_*.py` callbacks. Also update provider redirect URIs in your OAuth provider console to point at your deployed callback endpoints (e.g., `/api/oauth_google`).

These notes give a quick map to the most commonly-edited parts of the app. If you want, I can add a short `DEVELOPING.md` with the same content and a small checklist for PRs.

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
