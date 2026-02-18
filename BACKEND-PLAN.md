# Alto — Backend Plan

> **API:** `https://api.alto-ai.tech` | **Agent:** `https://agent.alto-ai.tech`

---

## Table of Contents

1. [What You're Building](#1-what-youre-building)
2. [Directory Structure](#2-directory-structure)
3. [Key Naming Convention](#3-key-naming-convention)
4. [Tool Plugin System](#4-tool-plugin-system)
5. [Trigger System](#5-trigger-system)
6. [Agent Pipeline](#6-agent-pipeline)
7. [Memory System](#7-memory-system)
8. [Session Management](#8-session-management)
9. [Data Storage](#9-data-storage)
10. [Bootstrap & Auto-Update](#10-bootstrap--auto-update)
11. [Authentication](#11-authentication)
12. [OAuth Flow](#12-oauth-flow)
13. [Settings API Endpoints](#13-settings-api-endpoints)
14. [Error Codes](#14-error-codes)
15. [Server Setup](#15-server-setup)
16. [Environment Variables](#16-environment-variables)
17. [Implementation Order](#17-implementation-order)

---

## 1. What You're Building

Three processes on one machine:

- **Settings API** (`api.alto-ai.tech`) — FastAPI REST server. Login, settings, tool manifests, OAuth. Never touches the AI.
- **Agent Server** (`agent.alto-ai.tech`) — Runs sessions. Handles triggers, memory, tool pre-selection, summarisation, and main reasoning.
- **Trigger listeners** — Long-running background tasks inside the Agent Server. One per integration. They watch for events and fire sessions.

### LLM Providers

| Provider | Used for | Why |
|---|---|---|
| **Mistral** | Main agent reasoning | Best reasoning quality |
| **Groq** | Tool pre-selection + conversation summarisation | Fast and cheap — saves Mistral input tokens |
| **sentence-transformers** (local) | Memory embedding + retrieval | No API cost, runs on-device |

The key constraint driving this design: **minimise tokens sent to Mistral**. Every technique below — pre-selection, summarisation, memory injection — serves this goal.

---

## 2. Directory Structure

```
alto/
├── agent/
│   ├── server.py            # Agent Server entry point
│   ├── pipeline.py          # Runs the 8-step session pipeline
│   ├── session.py           # Session state and lifecycle
│   ├── memory.py            # Embed, store, retrieve memories
│   ├── preselect.py         # Tool pre-selection via Groq
│   ├── summarise.py         # Conversation summarisation via Groq
│   └── llm.py               # Mistral client wrapper
├── api/
│   ├── app.py
│   ├── auth.py
│   └── routes/
│       ├── auth.py
│       ├── settings.py
│       ├── agent.py
│       ├── tools.py
│       ├── oauth.py
│       └── logs.py
├── tools/
│   ├── discord/
│   │   ├── tool.py          # execute(params, settings) -> dict
│   │   ├── trigger.py       # start_listener + receive_message
│   │   └── manifest.json
│   └── trello/
│       ├── tool.py
│       ├── trigger.py
│       └── manifest.json
├── memory/
│   └── store/               # ChromaDB files (gitignored)
├── data/
│   ├── settings.json        # Integration settings (gitignored)
│   ├── agent.json           # Agent behaviour config (gitignored)
│   ├── user.json            # Admin credentials (gitignored)
│   └── sessions.json        # Active sessions — written on shutdown (gitignored)
├── logs/
│   └── alto.log
├── .env
├── .env.example
├── requirements.txt
├── start.sh
└── watcher.sh
```

---

## 3. Key Naming Convention

### Integration settings (`settings.json`)
```
{tool_id}__{field_id}
```
Examples: `discord__allowed_user_ids`, `trello__oauth_token`, `trello__board_id`

### Agent behaviour (`agent.json`)
```
agent__{field_id}
```
Examples: `agent__name`, `agent__personality`, `agent__response_style`

### `.env` keys
App-level secrets. Uppercase, single underscore:
```
DISCORD_BOT_TOKEN
TRELLO_CLIENT_ID
TRELLO_CLIENT_SECRET
MISTRAL_API_KEY
GROQ_API_KEY
```

---

## 4. Tool Plugin System

Each tool is a folder under `tools/`. Folder name = tool ID (lowercase, underscores). Each folder contains:

- `tool.py` — called by the agent when Mistral decides to use this tool
- `trigger.py` — called at startup to start listening for events (optional — omit if the tool is action-only)
- `manifest.json` — describes the tool

### `tool.py`

```python
async def execute(params: dict, settings: dict) -> dict:
    # params: arguments from Mistral's tool call
    # settings: resolved values (env vars + settings.json merged)
    ...
```

### `trigger.py`

```python
async def start_listener(settings: dict, fire_trigger: callable) -> None:
    # Called once at startup.
    # Start a background listener (Discord bot, webhook endpoint, polling loop, etc.)
    # When an event occurs, call fire_trigger(TriggerEvent(...))
    ...

async def receive_message(event: dict, session: Session) -> None:
    # Called when an existing open session receives a new message
    # from this integration. Use this to e.g. acknowledge receipt in Discord.
    ...
```

### `manifest.json`

```json
{
  "id": "discord",
  "name": "Discord",
  "description": "Send and receive Discord messages.",
  "version": "1.0.0",
  "active_when": ["discord__bot_token", "discord__allowed_user_ids"],
  "trigger": {
    "description": "A Discord message that mentions Alto or replies to Alto.",
    "context_key": "discord__channel_id"
  },
  "oauth": null,
  "agent_schema": {
    "description": "Send a Discord message to a user.",
    "parameters": {
      "user_id": { "type": "string", "description": "Discord user ID" },
      "message":  { "type": "string", "description": "Message content" }
    },
    "required": ["user_id", "message"]
  },
  "settings_schema": [
    {
      "key": "discord__bot_token",
      "label": "Bot Token",
      "type": "secret",
      "source": "env",
      "env_var": "DISCORD_BOT_TOKEN",
      "description": "Set in server .env.",
      "required_for_activation": true
    },
    {
      "key": "discord__allowed_user_ids",
      "label": "Allowed User IDs",
      "type": "string_array",
      "source": "settings",
      "description": "Discord user IDs that can trigger Alto.",
      "required_for_activation": true
    }
  ]
}
```

**`trigger` block:**

| Field | Meaning |
|---|---|
| `description` | Plain English description used in the tool pre-selection prompt sent to Groq |
| `context_key` | Setting key whose runtime value groups sessions. Discord uses channel ID — messages in the same channel continue the same session. Omit if all events from this tool share one session. |

Tools without a `trigger` block are **action-only** — the agent can call them, but they never start sessions.

**`source` values:**

| `source` | Where value lives | Returned by API |
|---|---|---|
| `env` | `.env` file | Never |
| `settings` | `settings.json` | Yes (secrets masked) |
| `oauth` | `settings.json`, written by OAuth callback | Never (only `connected: true/false`) |

**`type` values:** `string`, `secret`, `string_array`, `boolean`, `integer`, `oauth`

---

## 5. Trigger System

### TriggerEvent

```python
@dataclass
class TriggerEvent:
    tool_id: str        # Which integration fired, e.g. "discord"
    context_id: str     # Groups sessions, e.g. Discord channel ID
    user_message: str   # The message or event content as plain text
    raw: dict           # Full raw event payload
    timestamp: datetime
```

### How sessions are grouped

Sessions are scoped to `(tool_id, context_id)`. Two Discord channels = two sessions. Discord and Trello always = separate sessions. The `context_id` is the resolved runtime value of the manifest's `context_key` setting for that event.

### What happens when a trigger fires

1. Look up existing session for `(tool_id, context_id)`.
2. If a session exists and `last_activity` is within the session window → append the message and continue the session (runs the pipeline again).
3. If no session or the window has expired → create a new session and run the pipeline from step 1.

### Adding a new trigger

Add `trigger.py` to the tool folder and a `trigger` block to `manifest.json`. The trigger loader at startup scans all active tools with a `trigger` block and calls `start_listener` for each. No other changes needed.

---

## 6. Agent Pipeline

Every session runs this pipeline in order. Steps 3–4 (Groq) run in parallel to save time.

```
Trigger fires (or existing session receives a new message)
    │
    ▼
1. SESSION INIT / CONTINUE
   Load or create session.
   Append incoming user message to history.
    │
    ▼
2. MEMORY RETRIEVAL  [local sentence-transformers]
   Embed the incoming message.
   Query ChromaDB for top-k relevant memories (default k=5).
   Memories are global — not filtered by integration.
   Format as a system block prepended to the context.
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
3. SUMMARISATION  [Groq]           4. TOOL PRE-SELECTION  [Groq]
   If history token count              Send: current message +
   exceeds threshold (default 6000):   one-line description per active tool.
   Summarise oldest 60% of turns.      Receive: JSON array of relevant tool IDs.
   Replace with summary block.         Fall back to all active tools on error.
   Keep newest 40% verbatim.
    │                                  │
    └──────────────┬───────────────────┘
                   ▼
5. MAIN REASONING  [Mistral]
   System prompt:
     - Agent behaviour (from agent.json)
     - Injected memories (from step 2)
     - Conversation summary (from step 3, if applicable)
   History:
     - Summary block (if summarised) + recent verbatim turns
   Tools:
     - Only the pre-selected tool definitions (from step 4)
   Mistral reasons and may call tools.
    │
    ▼
6. TOOL EXECUTION  [loop until no more tool calls]
   Validate params against agent_schema.
   Call tool's execute(params, settings).
   Append result to history as a tool message.
   Send updated history back to Mistral.
    │
    ▼
7. RESPONSE DELIVERY
   Send Mistral's final response back through the originating integration.
   (e.g. reply in Discord channel, comment on Trello card)
    │
    ▼
8. MEMORY WRITE  [local sentence-transformers]
   Embed the exchange: "User: {message}\nAlto: {response}"
   Store in ChromaDB with metadata: tool_id, context_id, timestamp.
   Update session last_activity.
```

### Summarisation detail

Groq prompt:
```
Summarise the following conversation history concisely. Preserve key facts,
decisions, and context. Do not lose any information the user stated about themselves
or their preferences.

[conversation turns]
```

The summary replaces the old turns as a single system message: `"Summary of earlier conversation: ..."`. The summary is stored on the `Session` object and accumulates across turns (new summaries include the old summary).

### Tool pre-selection detail

Groq prompt:
```
You are a tool router. Return a JSON array of tool IDs that are likely needed
to respond to the user's message. Only include tools that will plausibly be used.

User message: "{user_message}"

Available tools:
{for each active tool: "- {id}: {trigger.description or agent_schema.description}"}

Respond with ONLY a JSON array, e.g. ["discord", "notion"].
If no tools are needed, return [].
```

On invalid JSON response from Groq: log a warning and fall back to sending all active tools to Mistral.

---

## 7. Memory System

### Stack

- **ChromaDB** — local vector database, persisted to `memory/store/`
- **sentence-transformers `all-MiniLM-L6-v2`** — local embedding model, loaded once at startup

No external API calls for memory. Zero cost.

### Write (step 8 of pipeline)

```python
text = f"User: {user_message}\nAlto: {response}"
embedding = model.encode(text)
collection.add(
    ids=[str(uuid4())],
    embeddings=[embedding.tolist()],
    documents=[text],
    metadatas=[{"tool_id": tool_id, "context_id": context_id, "ts": now.isoformat()}]
)
```

### Retrieval (step 2 of pipeline)

```python
query_embedding = model.encode(incoming_message)
results = collection.query(query_embeddings=[query_embedding], n_results=5)
# Inject results as system message: "Relevant context from memory:\n- ..."
```

Memories are **not** filtered by `tool_id` or `context_id` at retrieval time. A memory from a Trello session can surface in a Discord session if semantically relevant. This is intentional — Alto has a unified memory.

### Housekeeping

No automatic pruning in v1. Provide a CLI command:

```bash
python -m agent.memory prune --older-than 90  # removes memories older than 90 days
python -m agent.memory stats                   # prints collection size
```

---

## 8. Session Management

### Session state

```python
@dataclass
class Session:
    id: str
    tool_id: str
    context_id: str
    history: list[dict]       # Full message history (all turns)
    summary: str | None       # Rolling conversation summary
    created_at: datetime
    last_activity: datetime
    is_active: bool
```

### Window

- Window: **15 minutes** from `last_activity` (configurable via `SESSION_WINDOW_MINUTES`).
- Every new message resets `last_activity`.
- Background task checks every 60 seconds and marks expired sessions `is_active = False`.
- Expired sessions are kept in memory for the remainder of the server lifetime (not deleted).

### Persistence across restarts

On `SIGTERM`: serialize all active sessions to `data/sessions.json`.  
On startup: load `data/sessions.json` if it exists, restore sessions, delete the file.

This ensures that auto-update restarts from `watcher.sh` don't lose in-progress sessions.

---

## 9. Data Storage

### `data/settings.json`
```json
{
  "discord__allowed_user_ids": ["123456789"],
  "trello__oauth_token": "secret_xyz",
  "trello__board_id": "abc123"
}
```

### `data/agent.json`
```json
{
  "agent__name": "Alto",
  "agent__personality": "Helpful, concise, and professional.",
  "agent__response_style": "short",
  "agent__language": "en"
}
```

### `data/user.json`
```json
{
  "username": "admin",
  "password_hash": "<bcrypt hash>",
  "pwd_version": 1,
  "created_at": "2025-01-01T00:00:00Z"
}
```

### `data/sessions.json`
Written on shutdown, deleted after reload. Not present during normal operation.

### `memory/store/`
ChromaDB persistent files. Never commit.

Gitignore all of `data/` (except `data/.gitkeep`) and `memory/store/`.

---

## 10. Bootstrap & Auto-Update

### `start.sh`

1. Check Python 3.11+, pip, git. Exit with message if missing.
2. Create `.venv/` if absent.
3. `pip install -r requirements.txt` inside venv.
4. Copy `.env.example` → `.env` if absent. Print message to fill it in and exit.
5. Run `python -m api.auth setup` if `data/user.json` doesn't exist.
6. Launch Settings API and Agent Server via `nohup`. Write PIDs to `alto.pid`.
7. Launch `watcher.sh` in background.
8. Print local URLs.

### `watcher.sh`

60s loop:
1. `git fetch origin main`
2. Compare HEAD SHA to remote.
3. If different: `git pull` → `pip install -r requirements.txt` → `SIGTERM` PIDs (triggers graceful session save) → relaunch.
4. Log every check and restart.

---

## 11. Authentication

JWT Bearer tokens. No server-side session state.

- **Access token** — 15 min. `Authorization: Bearer <token>` on all protected endpoints.
- **Refresh token** — 7 days. In-memory revocation set. Used only by `POST /auth/refresh`.

JWT payload: `sub`, `iat`, `exp`, `type` (`"access"` or `"refresh"`), `pwd_version`.

Every request: verify signature → check expiry → check `pwd_version` matches `user.json`. Any mismatch → `401 INVALID_TOKEN`.

```bash
python -m api.auth setup   # sets initial username + password
```

---

## 12. OAuth Flow

Tools with an `oauth` block in `manifest.json` use the browser redirect flow.

```
1. Frontend → GET /oauth/{tool_id}/start
   Backend: generate state token (in-memory, 10-min TTL)
   Return: { "authorization_url": "..." }

2. Frontend opens URL in new tab

3. User approves → provider redirects to:
   https://api.alto-ai.tech/oauth/{tool_id}/callback?code=...&state=...

4. Backend:
   → Validate state
   → Exchange code for token (using .env client secret)
   → Save token to settings.json under manifest's token_key
   → Trigger tool reload
   → Return HTML: "Connected! You can close this tab."

5. Frontend polls GET /tools/{tool_id} until active: true
```

#### `GET /oauth/{tool_id}/start` — protected
```json
{ "authorization_url": "https://..." }
```

#### `GET /oauth/{tool_id}/callback` — public
Returns HTML. Not JSON.

#### `DELETE /oauth/{tool_id}` — protected
```
204 No Content
```

Register this redirect URI with every OAuth provider:
```
https://api.alto-ai.tech/oauth/{tool_id}/callback
```

---

## 13. Settings API Endpoints

**Base URL:** `https://api.alto-ai.tech`

---

### Auth

#### `POST /auth/login` — public
```json
{ "username": "admin", "password": "..." }
// 200: { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 900 }
```

#### `POST /auth/refresh` — refresh token in body
```json
{ "refresh_token": "..." }
// 200: same shape as login
```

#### `POST /auth/logout` — protected
```json
{ "refresh_token": "..." }
// 204
```

#### `PUT /auth/password` — protected
```json
{ "current_password": "old", "new_password": "new" }
// 204 — increments pwd_version, all tokens immediately invalid
```

---

### Agent Behaviour

#### `GET /agent` — protected
```json
{
  "settings": { "agent__name": "Alto", "agent__personality": "...", "agent__response_style": "short", "agent__language": "en" },
  "schema": [
    { "key": "agent__name",           "label": "Agent Name",     "type": "string", "description": "What Alto calls itself.",          "default": "Alto" },
    { "key": "agent__personality",    "label": "Personality",    "type": "string", "description": "How Alto should behave.",           "default": "Helpful, concise, and professional." },
    { "key": "agent__response_style", "label": "Response Style", "type": "string", "description": "How verbose responses should be.", "default": "short" },
    { "key": "agent__language",       "label": "Language",       "type": "string", "description": "BCP 47 tag, e.g. en, nl, de.",     "default": "en" }
  ]
}
```

#### `PUT /agent` — protected
```json
{ "agent__personality": "Friendly and brief." }
// 200: { "updated": ["agent__personality"] }
```
Reject keys not starting with `agent__` → `400 INVALID_SETTING_KEY`.

---

### Tools

#### `GET /tools` — protected
```json
{
  "tools": [
    { "id": "discord", "name": "Discord", "active": true,  "has_trigger": true,  "version": "1.0.0" },
    { "id": "trello",  "name": "Trello",  "active": false, "has_trigger": true,  "version": "1.0.0" },
    { "id": "search",  "name": "Search",  "active": true,  "has_trigger": false, "version": "1.0.0" }
  ]
}
```

#### `GET /tools/{id}` — protected

Returns manifest with current values merged in. Primary data source for the frontend settings form.

```json
{
  "id": "trello",
  "name": "Trello",
  "description": "Manage Trello boards and cards.",
  "active": false,
  "has_oauth": true,
  "has_trigger": true,
  "settings": [
    {
      "key": "trello__oauth_token",
      "label": "Trello Connection",
      "type": "oauth",
      "source": "oauth",
      "description": "Connect your Trello account.",
      "connected": false,
      "required_for_activation": true
    },
    {
      "key": "trello__board_id",
      "label": "Default Board ID",
      "type": "string",
      "source": "settings",
      "description": "The Trello board Alto will use by default.",
      "current_value": null,
      "required_for_activation": false
    }
  ]
}
```

Field rules:
- `type: "oauth"` → return `connected: true/false`, never the token value
- `type: "secret"`, `source: "settings"` → `"●●●●●●"` if set, `null` if not
- `source: "env"` → always `current_value: null`

---

### Settings

#### `GET /settings` — protected
```json
{ "settings": { "discord__allowed_user_ids": ["123456789"], "trello__board_id": "abc123" } }
```
Excludes secrets, oauth tokens, and env-sourced fields.

#### `PUT /settings` — protected
```json
{ "trello__board_id": "xyz" }
// 200: { "updated": ["trello__board_id"], "tools_reloaded": true }
```
- `env` key → `409 SETTING_READONLY`
- `oauth` key → `409 SETTING_READONLY`
- Unknown key → `400 INVALID_SETTING_KEY`

#### `DELETE /settings/{key}` — protected
```
204 | 404 | 409
```

---

### Logs

#### `GET /logs/stream` — `?token=` query param
```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no

data: {"ts": "2025-01-01T12:00:00Z", "level": "INFO", "msg": "..."}
```

---

### Health

#### `GET /health` — public
```json
{ "status": "ok", "agent": "running", "uptime_seconds": 3600, "version": "git-abc1234" }
```
`agent`: `"running"` or `"unavailable"` (PID check).

---

## 14. Error Codes

```json
{ "error": { "code": "INVALID_TOKEN", "message": "JWT has expired.", "request_id": "req_abc123" } }
```

| HTTP | Code | When |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Malformed body or missing field |
| `400` | `INVALID_SETTING_KEY` | Key not defined in any manifest or agent schema |
| `401` | `MISSING_TOKEN` | No token on protected endpoint |
| `401` | `INVALID_TOKEN` | JWT malformed, expired, or pwd_version mismatch |
| `401` | `BAD_CREDENTIALS` | Wrong login |
| `401` | `TOKEN_REVOKED` | Refresh token was logged out |
| `404` | `NOT_FOUND` | Tool ID, setting key, or OAuth tool not found |
| `409` | `SETTING_READONLY` | Tried to write an `env` or `oauth` key via `PUT /settings` |
| `500` | `INTERNAL_ERROR` | Unexpected server error |

---

## 15. Server Setup

| Subdomain | Process | Port |
|---|---|---|
| `api.alto-ai.tech` | Settings API | 8000 |
| `agent.alto-ai.tech` | Agent Server | 8001 |

```
# Caddy
api.alto-ai.tech   { reverse_proxy localhost:8000 }
agent.alto-ai.tech { reverse_proxy localhost:8001 }
```

DNS: A records → public IP. DDNS: DuckDNS or Cloudflare. Router: port-forward `443` → PC `443`.

---

## 16. Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `JWT_SECRET` | Yes | `openssl rand -hex 32` |
| `MISTRAL_API_KEY` | Yes | Main reasoning |
| `GROQ_API_KEY` | Yes | Pre-selection + summarisation |
| `API_PORT` | No | Default `8000` |
| `AGENT_PORT` | No | Default `8001` |
| `LOG_LEVEL` | No | Default `INFO` |
| `CORS_ORIGINS` | Yes | Comma-separated allowed frontend origins |
| `SUMMARISE_TOKEN_THRESHOLD` | No | Default `6000` |
| `SESSION_WINDOW_MINUTES` | No | Default `15` |
| `MEMORY_TOP_K` | No | Default `5` |
| `DISCORD_BOT_TOKEN` | Per tool | App secrets for non-OAuth tools |
| `TRELLO_CLIENT_ID` | Per tool | One ID + secret pair per OAuth tool |
| `TRELLO_CLIENT_SECRET` | Per tool | |

Document every tool-specific variable in `.env.example`.

---

## 17. Implementation Order

1. Repo structure, `.gitignore`, `.env.example`, `data/.gitkeep`, `memory/.gitkeep`
2. `start.sh` and `watcher.sh`
3. `api/auth.py` — JWT, bcrypt, CLI setup
4. `/auth/*` routes
5. Tool loader — manifest parsing, `active_when`, trigger/oauth detection, reload hook
6. `/settings/*` routes
7. `/agent` routes
8. `/tools/*` routes
9. `/oauth/*` routes
10. `/logs/stream` SSE with `?token` auth
11. `/health` + `api/app.py` CORS wiring
12. `agent/memory.py` — ChromaDB + sentence-transformers
13. `agent/summarise.py` — Groq summarisation
14. `agent/preselect.py` — Groq tool pre-selection
15. `agent/llm.py` — Mistral client
16. `agent/session.py` — session state, window, SIGTERM persistence
17. `agent/pipeline.py` — full 8-step pipeline wiring all of the above
18. Trigger loader — scan active tools for `trigger.py`, call `start_listener` at startup
19. First tool: Discord (`tool.py` + `trigger.py`)
20. Caddy + DNS + DDNS