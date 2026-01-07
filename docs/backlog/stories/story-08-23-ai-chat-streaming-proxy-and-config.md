---
type: story
id: ST-08-23
title: "AI: editor chat streaming proxy + LLM_CHAT_* config"
status: done
owners: "agents"
created: 2026-01-03
updated: 2026-01-07
epic: "EPIC-08"
acceptance_criteria:
  - "Given LLM chat is enabled, when a contributor calls `POST /api/v1/editor/tools/{tool_id}/chat`, then the backend streams assistant text via SSE and the client can render it incrementally."
  - "Given the client cancels a streaming request (disconnects), when an upstream LLM request is in flight, then the backend stops streaming immediately and cancels the upstream call when possible."
  - "Given LLM chat is disabled or misconfigured, when `POST /api/v1/editor/tools/{tool_id}/chat` is called, then the backend responds without a 500 and without exposing provider details."
  - "Given a chat request is handled, then the backend persists a canonical server-side chat thread keyed by `{user_id, tool_id}` (30-day TTL since last activity) and uses it as context on subsequent chat-first requests."
  - "Given the newest user message cannot fit with the full system prompt and reserved output budget, when `POST /api/v1/editor/tools/{tool_id}/chat` is called, then the backend returns HTTP 422 with a user-actionable Swedish message and does not mutate stored chat history."
  - "Given a contributor calls `DELETE /api/v1/editor/tools/{tool_id}/chat`, then the backend clears the stored chat thread for that user and tool."
  - "Given a chat request is handled, then the backend logs metadata only (template id, lengths, outcome, latency) and never logs prompts, code, conversation text, or model output."
  - "Given chat is configured, then it uses a dedicated `LLM_CHAT_*` profile and prompt template ID (does not reuse `LLM_COMPLETION_*` or `LLM_EDIT_*`)."
  - "Given the endpoint is implemented, then the SSE event types and payload format are explicitly defined and stable to avoid frontend/backend drift."

dependencies:
  - "ST-08-18"
  - "ADR-0051"
  - "ADR-0052"
ui_impact: "No (backend endpoint + config only)"
data_impact: "Yes (server-side chat thread per {user_id, tool_id}; stored in tool_session_messages)"
---

## Context

ST-08-20 requires a streaming backend endpoint for an in-editor chat drawer.
This endpoint must be strictly separated
from inline completions so Tab/ghost-text behavior remains stable and fast.

## Scope

### Endpoint (streaming)

- Add a dedicated streaming endpoint:
  `POST /api/v1/editor/tools/{tool_id}/chat` (SSE response).
- Request body: `{ "message": "<user message>" }`.
- Auth + CSRF requirements should match the existing editor AI endpoints.
- This endpoint returns assistant text only (no structured edit ops).
  Structured edit proposals are handled by
    `POST /api/v1/editor/edit-ops` (ST-08-21).
- Add a clear endpoint: `DELETE /api/v1/editor/tools/{tool_id}/chat`.

### Thread storage (canonical)

- Store conversation server-side as the canonical chat thread for editor AI
  chat-first flows (text now, edit-ops later).
- Storage: append-only `tool_session_messages` rows keyed by `tool_sessions`
  (`context="editor_chat"`, `{user_id, tool_id}`).
- TTL: 30 days since last activity, enforced on access by comparing the last
  message timestamp, and clear on user demand (delete endpoint).
- Persistence semantics:
  - Persist the user message immediately.
  - Persist the assistant message only on successful completion.
  - Use message identifiers for correlation (`message_id` + `in_reply_to`) so assistant
    messages are inserted after the matching user message, even under concurrency.
  - Best-effort, per-process single-flight guard may return 409 to shed concurrent requests;
    it is not relied on for correctness in multi-worker deployments.

### SSE wire format (explicit)

- Response:
  - `Content-Type: text/event-stream; charset=utf-8`
  - `Cache-Control: no-cache`
- Events (JSON payloads; 1 JSON object per event):
  - `event: meta` (exactly once, first)
    - `data: {"enabled": true}`
  - `event: delta` (0..n)
    - `data: {"text": "<utf8-chunk>"}`
  - `event: done` (exactly once, last)
    - `data: {"enabled": true, "reason": "stop"|"cancelled"|"error"}`
- Disabled / misconfigured:
  - Send a single `event: done` with `data: {"enabled": false, "message":
"AI‑chat är inte tillgänglig just nu. Försök igen senare."}` then close.
  - MUST NOT return a 500 or leak provider details.
- Cancellation:
  - On client disconnect, stop emitting events immediately and cancel upstream
work when possible (best-effort).

### History + budgeting behavior (MVP)

- The backend owns provider context construction from the stored thread.
- When calling the provider:
  - Use a sliding window (drop oldest turns first).
  - Never truncate the system prompt.
  - If the newest user message alone cannot fit with the full system prompt +
    reserved output budget: return HTTP 422 with
    `För långt meddelande: korta ned eller starta en ny chatt.` and do not
    mutate stored history.

### Configuration (separate from completions/edits)

Introduce a dedicated config group for chat (names and defaults to be
finalized during implementation):

- `LLM_CHAT_ENABLED`
- `LLM_CHAT_BASE_URL`
- `OPENAI_LLM_CHAT_API_KEY` (optional for self-hosted)
- `LLM_CHAT_MODEL`
- `LLM_CHAT_TEMPLATE_ID` (new prompt template ID integrated into the existing
  prompt system from ST-08-18)
- Recommended starting budgets (hemma Vulkan baseline):
  - `LLM_CHAT_CONTEXT_WINDOW_TOKENS=16384`
  - `LLM_CHAT_MAX_TOKENS=1500`

### Provider compatibility

- Provider must be OpenAI-compatible HTTP (`/v1/chat/completions`).
- llama-server optimization: include `cache_prompt: true` only when
  `LLM_CHAT_BASE_URL` is local `:8082` (so OpenAI/OpenRouter never see
  unknown fields).

### Privacy + observability

- Never log prompt text, code text, conversation messages, or model output
  (ADR-0051).
- Log metadata only (template id, length metrics, outcome, latency when
  available).

## Notes

- The frontend must be able to cancel requests (AbortController); backend
  should treat client disconnect as a signal to
    stop work where possible to avoid wasting tokens/latency.
- Related PR: `docs/backlog/prs/pr-0008-editor-chat-message-storage-minimal-c.md`
