# MVP Calendar Workspace

> **Branch:** `demo/rag-expansion` — RAG knowledge base + AI-powered Q&A layer on top of the existing calendar and student planning system.

A Vercel-deployed MCP server + conversational chat UI for the **MyVillage Project** educational program. Coaches and program managers can ask natural-language questions, generate personalized student lesson plans, and export calendar invites — all from one interface.

| | |
|---|---|
| **API endpoint** | `POST /api/mcp` |
| **Frontend** | `public/index.html` — conversational chat UI |
| **Branch** | `demo/rag-expansion` |
| **Python** | 3.12+ · FastAPI · FastMCP · httpx |
| **Deploy** | Vercel serverless (zero config) |

---

## What This Demo Shows

This project was built to demonstrate three things end-to-end:

### 1 — Backend Flow
A FastAPI + [FastMCP](https://github.com/jlowin/fastmcp) server maps every chat message to an MCP tool call via `POST /api/mcp`. Intent detection happens on the frontend before the request is sent — student planning, RAG queries, and calendar commands each route to a different tool. The entire flow is visible in [main.py](main.py) and [api/mcp.py](api/mcp.py).

### 2 — Data Interaction (RAG)
Retrieval-Augmented Generation is implemented end-to-end with **no external vector database**:

```
User question
     │
     ▼
TF-IDF retriever  ──→  top-k chunks from knowledge_base.json
     │
     ▼
LLM (OpenRouter / Gemini)  ──→  synthesized, grounded answer
     │
     ▼
Response with source citations shown in the UI
```

- Knowledge base: [`data/knowledge_base.json`](data/knowledge_base.json) — 10 program documents
- Retriever: pure-Python TF-IDF cosine similarity (`_retrieve_chunks` in [main.py](main.py)) — no numpy, no heavy deps, runs on Vercel's serverless runtime
- LLM synthesis: `ask_knowledge_base` tool calls OpenRouter when `LLM_API_KEY` is set; falls back to best-excerpt summary without it
- Student data: pulled live from an n8n webhook, indexed by student, used to generate personalized lesson plans via the LLM

### 3 — Live UI
The chat UI at `public/index.html` handles all three flows in one conversation:
- RAG answers with **source chips** (document title + section)
- Student plan generation with a multi-select student picker
- Calendar event creation, recurrence, and `.ics` export

---

## Chat Flow

The frontend uses a three-path intent router before every send:

```
User message
     │
     ├─ looksLikeStudentPlanRequest()  ──→  submitPersonalizedLessonPlans()
     │
     ├─ looksLikeKnowledgeBaseQuery()  ──→  submitKnowledgeBaseQuery()
     │                                        └─ calls ask_knowledge_base tool
     │                                        └─ renders answer + source chips
     │
     └─ everything else  ──→  handle_message tool
                               ├─ add / list / delete calendar events
                               ├─ summarize upcoming
                               └─ fallback help text
```

### Calendar Commands

The `handle_message` tool understands natural language and terse shorthands:

| Intent | Examples |
|---|---|
| List all events | `list` · `list events` · `what's coming up` |
| List by date | `list events on 2026-01-01` · `What's on March 5?` |
| Add event | `Add Birthday on 2026-02-01` · `Add Lunch tomorrow` |
| Add with time | `Add Meeting on 2026-03-03 at 2pm` |
| Add time range | `Add Meeting on 2026-03-03 from 3pm to 5pm` |
| Delete | `delete Meeting` · `remove Birthday` |
| Summarize | `summarize` · `summary` · `brief` |
| Shorthand add | `add:Title\|YYYY-MM-DD\|Description` |

### Student Lesson Planning

Triggered by phrases like *"lesson plans"*, *"student plans"*, *"personalized lesson"*:

1. Fetch available students from the n8n webhook (`STUDENT_SKILLS_WEBHOOK_URL`)
2. Multi-select student picker in chat
3. Optional: set per-student personalized goals
4. Backend generates LLM-personalized lesson plans (or heuristic fallback)
5. Calendar milestone creation per student
6. Export each student's sessions as individual `.ics` files

### Knowledge Base Q&A (RAG)

Triggered by question patterns like *"What is…"*, *"How does…"*, *"Tell me about…"*:

1. Frontend calls `ask_knowledge_base` directly (bypasses `handle_message`)
2. TF-IDF retriever ranks all 10 KB documents against the query
3. Top-3 chunks passed to LLM as context
4. LLM returns a grounded answer (or best excerpt if no `LLM_API_KEY`)
5. UI renders answer with a **RAG ✦ AI Answer** badge and source chips

**Try these queries in the chat:**
- `What is MyVillage Project?`
- `How does enrollment work?`
- `What are coaches responsible for?`
- `How does the AI planning assistant work?`
- `What do students present at the capstone?`

---

## Knowledge Base

[`data/knowledge_base.json`](data/knowledge_base.json) — 10 documents covering the full program:

| ID | Document | Source |
|---|---|---|
| `prog-overview` | Program Overview | Program Guide §1 |
| `enrollment-process` | Enrollment & Onboarding | Program Guide §2 |
| `coaching-model` | The MVP Coaching Model | Coaching Handbook Ch.1 |
| `skills-database` | Student Skills Database & Check-In System | Tech Infrastructure Guide |
| `rag-and-ai` | AI-Powered Planning Assistant | Tech Infrastructure Guide |
| `calendar-export` | Calendar Invites & .ics Export | Program Guide §4 |
| `coach-expectations` | Coach Responsibilities & Expectations | Coaching Handbook Ch.2 |
| `capstone-projects` | Capstone Project Requirements | Program Guide §5 |
| `data-privacy` | Student Data Privacy & FERPA Compliance | Policy Manual §3 |
| `site-locations` | Program Sites & Locations | Program Guide §1 |
| `outcomes` | Program Outcomes & Impact Data | 2024 Impact Report |

To add documents: append objects to the JSON array with `id`, `title`, `source`, and `content` fields. The retriever reloads at module import — no code changes needed.

---

## Backend Tools

All tools are called via `POST /api/mcp` with shape `{ "tool": "tool_name", "input": { ... } }`.

| Tool | Description |
|---|---|
| `handle_message` | Routes natural-language messages to calendar actions |
| `ask_knowledge_base` | RAG: retrieves chunks → LLM synthesizes answer → returns with sources |
| `search_knowledge_base` | Returns raw ranked chunks for a query (no LLM synthesis) |
| `personalized_lesson_plans` | Fetches student data from webhook + generates LLM lesson plans |
| `add_event` | Creates a calendar event (called internally by `handle_message`) |
| `set_recurrence` | Sets a recurrence pattern on an existing event |
| `create_tasks` | Creates multi-step milestones from a project goal |
| `research_and_breakdown` | LLM-powered project planning and milestone generation |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_API_KEY` | Recommended | OpenRouter API key — enables LLM synthesis in RAG and lesson plans |
| `OPENROUTER_MODEL` | Optional | Model to use (default: `google/gemini-flash-1.5`) |
| `STUDENT_SKILLS_WEBHOOK_URL` | Optional | n8n webhook for live student skill data |
| `MS_CLIENT_ID` | Optional | Azure AD client ID for Microsoft Calendar OAuth |
| `MS_CLIENT_SECRET` | Optional | Azure AD client secret |
| `MS_TENANT_ID` | Optional | Azure AD tenant (default: `common`) |
| `MS_REDIRECT_URI` | Optional | OAuth callback URI |

Without `LLM_API_KEY`, RAG answers fall back to the best-matching document excerpt and lesson plans use the heuristic template generator. Everything else works without any keys.

---

## Local Setup

```bash
# 1. Clone and activate venv
git clone <repo> && cd vercel-event-calendar-mcp
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) set your LLM key
export LLM_API_KEY=sk-or-...

# 4. Run the local dev server
python test_local.py
# → open http://localhost:3000
```

**Try it immediately — no keys needed:**
- `What is MyVillage Project?` → KB answer with sources
- `Add Team Meeting on 2026-06-01 from 2pm to 3pm` → calendar event
- `lesson plans` → student planning flow (uses webhook)

### Deploy to Vercel

```bash
npm install -g vercel
vercel deploy
# → https://<project>.vercel.app
```

Set environment variables in the Vercel dashboard under **Settings → Environment Variables**.

### Microsoft Calendar OAuth (Optional)

Set `MS_CLIENT_ID` + `MS_CLIENT_SECRET` in your environment. The **Connect to MyVillage Project Account** button will:
1. Call `GET /api/oauth/microsoft/start` → build Microsoft auth URL
2. Redirect to Microsoft login
3. Callback at `GET /api/oauth/microsoft/callback` → exchange code, fetch display name
4. Show `Connected: <name>` in the chat header

Without these vars the button falls back to `redirect_microsoft.html`.

---

## Project Structure

```
├── main.py                   # MCP tools + FastAPI app
├── api/
│   ├── app.py                # Vercel ASGI entrypoint
│   └── mcp.py                # Serverless handler for /api/mcp
├── data/
│   └── knowledge_base.json   # RAG document store (10 program docs)
├── public/
│   ├── index.html            # Chat UI
│   ├── script.js             # Intent routing, RAG rendering, planning flows
│   └── style.css             # UI styles (incl. RAG source chips)
├── requirements.txt
└── vercel.json
```

---

## Editor Guide

### Adding a new KB document

Append to [`data/knowledge_base.json`](data/knowledge_base.json):

```json
{
  "id": "unique-slug",
  "title": "Document Title",
  "source": "Section Reference",
  "content": "Full document text here..."
}
```

No code changes needed — the retriever loads all documents at import time.

### Adding a new chat intent

1. **Frontend** ([public/script.js](public/script.js)) — add a `looksLike*()` function and a `submit*()` handler, then wire them into the form submit block
2. **Backend** ([main.py](main.py)) — add a `@mcp.tool()` decorated function

### Key functions

| File | Function | Purpose |
|---|---|---|
| [main.py](main.py) | `_retrieve_chunks(query, top_k)` | TF-IDF cosine similarity retrieval |
| [main.py](main.py) | `ask_knowledge_base(query)` | RAG tool: retrieve + LLM synthesize |
| [main.py](main.py) | `search_knowledge_base(query)` | Raw chunk retrieval tool |
| [main.py](main.py) | `handle_message(message)` | Calendar command parser + RAG router |
| [main.py](main.py) | `personalized_lesson_plans(...)` | Student data + LLM lesson plans |
| [public/script.js](public/script.js) | `submitKnowledgeBaseQuery(text)` | Frontend RAG call + render |
| [public/script.js](public/script.js) | `renderRagResponse(answer, sources, rag)` | Renders answer with source chips |
| [public/script.js](public/script.js) | `submitPersonalizedLessonPlans(text)` | Multi-step student planning flow |

### Replacing in-memory event storage

Events are stored in a Python list and reset on every cold start. For production:

- Replace `events: List[Dict] = []` with a DB connection (PostgreSQL, Redis, DynamoDB)
- Update `add_event()`, `view_events()`, `delete_event()`, and `set_recurrence()` to use DB ops
- On Vercel, AWS DynamoDB or a managed Postgres (Neon, Supabase) works well

---

## Contributing

Branch per feature. Commit prefixes: `feat:` · `fix:` · `style:` · `docs:` · `refactor:`. Open a PR before merging to `main`.

See [`DEVELOPING.md`](DEVELOPING.md) for a full developer guide.
