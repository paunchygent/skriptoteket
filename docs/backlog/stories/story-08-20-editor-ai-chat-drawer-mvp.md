---
type: story
id: ST-08-20
title: "Editor: AI chat drawer MVP (beginner-friendly assistant UI)"
status: ready
owners: "agents"
created: 2026-01-01
updated: 2026-01-07
epic: "EPIC-08"
acceptance_criteria:
  - "Given a tool author is in the script editor, when they open the AI chat drawer, then a chat UI is shown without navigating away from the editor."
  - "Given the user writes a message and presses Send, when the request is in flight, then the UI prevents duplicate sends and shows a clear streaming state."
  - "Given an assistant reply is streaming, when the user clicks Cancel, then the stream stops immediately and the UI does not get stuck in a loading state."
  - "Given the user sends a message, when the UI calls `POST /api/v1/editor/tools/{tool_id}/chat`, then it sends only the newest user message (no client-managed transcript rules) and the backend uses the stored server-side chat thread as context."
  - "Given AI chat is disabled by server config, when a message is sent, then the UI shows a clear 'not enabled' response without crashing and without exposing provider details."
  - "Given AI chat is enabled, when a message is sent, then the backend streams an assistant reply over SSE and the UI renders the streamed content as a single assistant message in the conversation."
  - "Given the page is reloaded, when the user returns to the same tool (any version), then the conversation history is restored from the canonical server-side chat thread (keyed by `{user_id, tool_id}`; 30-day TTL since last activity)."
  - "Given the user clicks Clear chat, then the UI clears the canonical server-side thread via `DELETE /api/v1/editor/tools/{tool_id}/chat`."
  - "Given chat history is cached client-side for UX, then full transcripts MUST NOT be stored in localStorage (use IndexedDB if needed; localStorage is allowed only for small UI preferences such as Focus mode)."
  - "Given a message is sent, then the backend logs metadata only (template id, lengths, outcome) and never logs message text, prompts, or code."

dependencies:
  - "ST-08-18"
  - "ST-08-23"
  - "ST-14-31"
  - "ST-14-30"
ui_impact: "Yes (script editor drawer)"
data_impact: "Yes (canonical server-side chat thread per {user_id, tool_id})"
---

## Context

AI capabilities exist (ghost text + edit suggestions) but are not beginner-
friendly because they assume the author can
already start writing code and can select the right code region. We need a
chat-first entry point that guides novices and
organizes AI interactions in a single, predictable place.

## Notes

This story delivers the chat drawer UI + conversation state plumbing.

 - Uses the streaming chat endpoint `POST /api/v1/editor/tools/{tool_id}/chat`
   (SSE)
  (implemented in ST-08-23).
- Non-goal: change inline completions (ghost text) behavior or prompt profiles
  (`POST /api/v1/editor/completions`).
- Structured edit operations, diff preview, and apply/undo are handled in
  follow-up stories (ST-08-21/22).
- **Decided persistence keying:** conversation history is keyed by `{user_id,
  tool_id}`; store `base_version_id` as metadata inside the stored payload (not
  in the key) so editor saves/new versions do not reset the chat.

See also:

- IndexedDB helper + shared DB: `docs/backlog/stories/story-14-30-editor-
working-copy-persistence-indexeddb.md`
- Focus mode (width): `docs/backlog/stories/story-14-31-editor-focus-mode-
collapse-sidebar.md`
- Chat streaming backend: `docs/backlog/stories/story-08-23-ai-chat-streaming-
proxy-and-config.md`

## Implementation decisions

- Storage:
  - Use the canonical server-side chat thread keyed by `{user_id, tool_id}`
    (30-day TTL since last activity; clear on demand).
  - Client-side IndexedDB may be used as a cache for UX, but the server-side
    thread is the source of truth.
  - **No localStorage transcript** (explicit story constraint).
- Context sent to backend:
  - Send only the newest user message.
  - The backend owns context trimming (sliding window; drop oldest turns; never
    truncate the system prompt).
- Base version metadata (no new table):
  - Source of truth: client sends `base_version_id` in the POST body
    (optional).
  - Storage: write `tool_sessions.state = {"base_version_id": "<uuid>"}` for
    context `editor_chat` only; do not store message history there.
  - Update behavior:
    - If `base_version_id` is provided, update state on each POST (best effort).
    - If omitted, do not modify existing state (keep last known
      `base_version_id`).
  - Clear behavior:
    - `DELETE /api/v1/editor/tools/{tool_id}/chat` clears messages and clears
      `tool_sessions.state`.
  - GET history response:
    - Include `base_version_id` in response metadata if present; omit otherwise.
  - TTL alignment:
    - If TTL expiry triggers delete, also clear state (so `base_version_id`
      is removed alongside history).
- Layout:
  - Implement chat as an editor workspace drawer (reuse the existing right-
    side drawer surface; do not introduce a second sidebar).
  - When opening chat in compare mode, enable Focus mode (ST-14-31) if it is
    not already enabled to preserve diff/editor legibility.

## Implementation plan

### Backend

1) **GET history endpoint (thin web layer)**
- Add `GET /api/v1/editor/tools/{tool_id}/chat?limit=60`.
- Use a dedicated application handler (no repository calls in router).
- Return Pydantic response models (`response_model=...`) for OpenAPI typing.
- **TTL enforcement:** when loading history, if the last message is older than
  TTL, delete all messages + clear `tool_sessions.state`, then return empty.

2) **Base_version_id metadata**
- Extend `EditorChatRequest` with optional `base_version_id`.
- On POST: if provided, update `tool_sessions.state` for
  `context="editor_chat"` (best effort).
- On GET: include `base_version_id` in response metadata if present.
- On DELETE: clear `tool_sessions.state` (alongside message deletion).

3) **Router rules**
- Keep `src/skriptoteket/web/api/v1/editor/chat.py` free of
  `from __future__ import annotations`.

### Frontend

1) **Composable local state**
- Implement `useEditorChat` with in-memory state (messages, status, errors).
- `loadHistory()` calls GET on drawer open (and/or editor load).
- **No localStorage transcript**; only IndexedDB if caching is added later.

2) **Streaming transport**
- Use **POST + SSE over `fetch`** with a small parser.
- Treat “stream ended before done” as **cancelled**.
- Ignore late deltas after `AbortController.abort()`.

3) **Clear while streaming**
- Abort the stream first, then DELETE, then clear UI state.

4) **Drawer integration**
- Add AI chat drawer to the existing right-side drawer system.
- Add toolbar entry point.
- Ensure opening chat in compare mode auto-enables Focus mode.

### Transport note: SSE vs WebSocket

- **SSE over POST** fits the existing cookie + CSRF model and matches
  “one prompt → one streamed reply”.
- **WebSockets** add bidirectional control but require auth + CSRF redesign
  and lifecycle handling (reconnect/state); defer until we need mid-stream
  command semantics.

### Session rule (required)

- Any UI/drawer change must be verified with live dev (backend + Vite) and
  recorded in `.agent/handoff.md`.
