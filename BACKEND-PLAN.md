# BACKEND-PLAN.md

> **API:** `https://api.alto-ai.tech` | **Agent:** `https://agent.alto-ai.tech`

---

## Table of Contents

1. [What You're Building](#1-what-youre-building)  
2. [Directory Structure](#2-directory-structure)  
3. [Key Naming Convention](#3-key-naming-convention)  
4. [Tool Plugin System](#4-tool-plugin-system) ← UPDATED  
5. [Trigger System](#5-trigger-system)  
6. [Agent Pipeline](#6-agent-pipeline)  
7. [Memory System](#7-memory-system)  
8. [Session Management](#8-session-management)  
9. [Data Storage](#9-data-storage)  
10. [Bootstrap & Auto-Update](#10-bootstrap--auto-update)  
11. [Authentication](#11-authentication)  
12. [OAuth Flow](#12-oauth-flow)  
13. [Settings API Endpoints](#13-settings-api-endpoints) ← UPDATED  
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

(unchanged details omitted)

---

## 2. Directory Structure

(unchanged)

---

## 3. Key Naming Convention

Integration settings (`settings.json`)
```
{tool_id}__{field_id}
```
New convention for enable flag:
- Each tool may have a boolean flag named `{tool_id}__enabled`
  - Example: `discord__enabled`, `trello__enabled`
  - Stored in `data/settings.json` like other settings
  - Source: `settings` (i.e. writable via PUT /settings)

Agent behaviour keys remain `agent__{field_id}`

---

## 4. Tool Plugin System (UPDATED)

Each tool is a folder under `tools/`. Folder name = tool ID (lowercase, underscores). Each folder contains:
- `tool.py` — called by the agent when Mistral decides to use this tool
- `trigger.py` — optional background listener
- `manifest.json` — describes the tool

Manifests continue to declare `settings_schema`, `agent_schema`, `trigger` and `active_when` arrays. Example manifest (unchanged except explanation of `active_when`):

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
  "agent_schema": { ... },
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

Activation change (NEW)
- The backend now requires two gates for a tool to be considered `active`:
  1. Configuration gate: all required configuration items (the manifest's `active_when` keys and any `required_for_activation` fields) must be present / satisfied (oauth connected / secrets present / env values set).
  2. Explicit enablement gate: the boolean setting `{tool_id}__enabled` must be present and true.
- Computation:
  - active = (has_required_configuration) AND (settings.get("{tool_id}__enabled", DEFAULT_ENABLED))
- Migration/default behavior:
  - To avoid breaking existing installations, the backend supports a configurable default for missing enable flags:
    - DEFAULT_ENABLED can be set to `true` (preserve prior behavior) or `false` (opt-in). Document this in `.env.example` as `DEFAULT_TOOL_ENABLED=true|false`.
    - Recommended safe default for new deployments: `false` (admin must explicitly enable tools). For upgrades where preserving behavior matters, set `DEFAULT_TOOL_ENABLED=true` until admin migrates.
- Backend injection for frontend:
  - When responding to `GET /tools/{id}`, the API will inject a `settings` entry describing the enable flag so the frontend can render it without special-casing:
    ```json
    {
      "key": "<tool_id>__enabled",
      "label": "Enabled",
      "type": "boolean",
      "source": "settings",
      "description": "Allow Alto to call this integration.",
      "current_value": true|false,
      "required_for_activation": false
    }
    ```
  - The injected enabled entry follows the same `settings` structure as other settings and can be read/modified with the existing Settings API.

Tool loader changes
- When the tool loader reads manifests and current `data/settings.json` it will:
  1. Resolve required configuration presence (env, oauth connected, settings present).
  2. Read `settings.get("{tool_id}__enabled")`. If absent, use configured DEFAULT_ENABLED.
  3. Compute `active` and return it in `GET /tools` and `GET /tools/{id}`.
  4. Inject `<tool_id>__enabled` into the `settings` array returned from `GET /tools/{id}` (so the frontend can render it).
- No change to existing `active_when` semantics other than adding the extra gate.

---

## 5. Trigger System

(unchanged — sessions grouped by (tool_id, context_id), etc.)

---

## 6. Agent Pipeline

(unchanged)

---

## 7. Memory System

(unchanged)

---

## 8. Session Management

(unchanged)

---

## 9. Data Storage (UPDATED examples)

`data/settings.json` example:
```json
{
  "discord__allowed_user_ids": ["123456789"],
  "trello__oauth_token": "secret_xyz",
  "trello__board_id": "abc123",
  "discord__enabled": true,      // new boolean enable flag
  "trello__enabled": false
}
```

Notes:
- `enabled` flags are stored like other settings in `data/settings.json` and are editable through `PUT /settings`.

---

## 10. Bootstrap & Auto-Update

(unchanged — note: `.env.example` should include `DEFAULT_TOOL_ENABLED` documented)

---

## 11. Authentication

(unchanged)

---

## 12. OAuth Flow

(unchanged)

---

## 13. Settings API Endpoints (UPDATED)

**Base URL:** `https://api.alto-ai.tech`

GET /tools
- Returns list of tools with server-computed `active` (as described above).
- Example:
```json
{
  "tools": [
    { "id": "discord", "name": "Discord", "active": true,  "has_trigger": true,  "version": "1.0.0" },
    { "id": "trello",  "name": "Trello",  "active": false, "has_trigger": true,  "version": "1.0.0" }
  ]
}
```

GET /tools/{id}
- Returns manifest with current values merged in. Backend will inject the `<tool_id>__enabled` boolean into `settings`.
- Example (injection shown):
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
      "key": "trello__enabled",
      "label": "Enabled",
      "type": "boolean",
      "source": "settings",
      "description": "Allow Alto to call this integration.",
      "current_value": false,
      "required_for_activation": false
    },
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

PUT /settings — protected
- Writable keys: any `source: "settings"` key including `<tool_id>__enabled`.
- Example to enable a tool:
```json
{ "trello__enabled": true }
```
- Responses and errors:
  - `200: { "updated": ["trello__enabled"], "tools_reloaded": true }`
  - `409 SETTING_READONLY` on `env` or `oauth` source keys, same as before
  - `400 INVALID_SETTING_KEY` for unknown keys
- On update: reload tool loader so `active` is re-evaluated and `GET /tools` responses reflect new state.

GET /settings — protected
- Returns current non-secret settings (unchanged). Will include `{tool_id}__enabled` values.

DELETE /settings/{key} — protected
- Clears a settings key. Clearing `<tool_id>__enabled` will make backend fall back to DEFAULT_ENABLED behavior (see migration note).

---

## 14. Error Codes

(unchanged)

---

## 15. Server Setup

(unchanged — note: add `DEFAULT_TOOL_ENABLED` to `.env.example`)

---

## 16. Environment Variables (addition)

| Variable | Required | Notes |
|---|---|---|
| DEFAULT_TOOL_ENABLED | No | Defaults to `true` for backward compatibility; set to `false` for new installs if you want opt-in enablement. Accepts `true` or `false`. |
| MISTRAL_MODEL | No | Default Mistral model to use — e.g. `mistral-large-latest`. |
| GROQ_MODEL | No | Default Groq model to use — e.g. `groq/compound`. |

Document this in `.env.example` and deployment notes.

---

## 17. Implementation Order (additions)

Add to order:
- Update tool loader to compute `enabled` gate and inject `<tool_id>__enabled` into `GET /tools/{id}` responses.
- Add `DEFAULT_TOOL_ENABLED` to `.env.example`.
- Ensure `PUT /settings` accepts and persists boolean values for `<tool_id>__enabled`.
- Add migration note for upgrades.

---

## Migration / rollout notes (recommended)
- For new deployments: set `DEFAULT_TOOL_ENABLED=false` in `.env` so admin must explicitly enable each tool.
- For existing deployments to avoid surprising changes: set `DEFAULT_TOOL_ENABLED=true` initially; optionally run a migration script that writes `{tool_id}__enabled: true` for tools that are currently active, then flip DEFAULT_TOOL_ENABLED to the safer default if desired.
- Provide a small admin UI or a CLI command to bulk toggle enabled flags when onboarding.

---