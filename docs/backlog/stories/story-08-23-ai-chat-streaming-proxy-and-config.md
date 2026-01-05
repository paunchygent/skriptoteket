---
type: story
id: ST-08-23
title: "AI: editor chat streaming proxy + LLM_CHAT_* config"
status: ready
owners: "agents"
created: 2026-01-03
updated: 2026-01-04
epic: "EPIC-08"
acceptance_criteria:
  - "Given LLM chat is enabled, when a contributor calls `POST /api/v1/editor/chat`, then the backend streams assistant text via SSE and the client can render it incrementally."
  - "Given the client cancels a streaming request (disconnects), when an upstream LLM request is in flight, then the backend stops streaming immediately and cancels the upstream call when possible."
  - "Given LLM chat is disabled or misconfigured, when `POST /api/v1/editor/chat` is called, then the backend responds without a 500 and without exposing provider details."
  - "Given a chat request is handled, then the backend logs metadata only (template id, lengths, outcome, latency) and never logs prompts, code, conversation text, or model output."
  - "Given chat is configured, then it uses a dedicated `LLM_CHAT_*` profile and prompt template ID (does not reuse `LLM_COMPLETION_*` or `LLM_EDIT_*`)."
  - "Given the endpoint is implemented, then the SSE event types and payload format are explicitly defined and stable to avoid frontend/backend drift."

dependencies:
  - "ST-08-18"
  - "ADR-0051"
  - "ADR-0052"
ui_impact: "No (backend endpoint + config only)"
data_impact: "No (stateless; no server-side persistence)"
---

## Context

ST-08-20 requires a streaming backend endpoint for an in-editor chat drawer.
This endpoint must be strictly separated
from inline completions so Tab/ghost-text behavior remains stable and fast.

## Scope

### Endpoint (streaming)

- Add a dedicated streaming endpoint: `POST /api/v1/editor/chat` (SSE
  response).
- Auth + CSRF requirements should match the existing editor AI endpoints.
- This endpoint returns assistant text only (no structured edit ops).
  Structured edit proposals are handled by
    `POST /api/v1/editor/edit-ops` (ST-08-21).

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
"<swedish-actionable-message>"}` then close.
  - MUST NOT return a 500 or leak provider details.
- Cancellation:
  - On client disconnect, stop emitting events immediately and cancel upstream
work when possible (best-effort).

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
  - `LLM_CHAT_MAX_TOKENS=1024`

### Privacy + observability

- Never log prompt text, code text, conversation messages, or model output
  (ADR-0051).
- Log metadata only (template id, length metrics, outcome, latency when
  available).

## Notes

- The frontend must be able to cancel requests (AbortController); backend
  should treat client disconnect as a signal to
    stop work where possible to avoid wasting tokens/latency.
