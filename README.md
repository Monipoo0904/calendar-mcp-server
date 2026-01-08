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
- The demo includes a `handle_message` tool for simple chat-like commands: `list`, `summarize`, `add:Title|YYYY-MM-DD|Desc`, `delete:Title`.

Frontend improvements:

- Chat UI now supports typing indicator, timestamps, avatars, copy-to-clipboard buttons, Shift+Enter for newlines, Enter to send, and conversation persistence in `localStorage`. The composer shows a spinner while the backend responds and disables input until a reply is received.
