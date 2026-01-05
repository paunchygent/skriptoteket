---
type: story
id: ST-08-20
title: "Editor: AI chat drawer MVP (beginner-friendly assistant UI)"
status: ready
owners: "agents"
created: 2026-01-01
updated: 2026-01-04
epic: "EPIC-08"
acceptance_criteria:
  - "Given a tool author is in the script editor, when they open the AI chat drawer, then a chat UI is shown without navigating away from the editor."
  - "Given the user writes a message and presses Send, when the request is in flight, then the UI prevents duplicate sends and shows a clear streaming state."
  - "Given an assistant reply is streaming, when the user clicks Cancel, then the stream stops immediately and the UI does not get stuck in a loading state."
  - "Given the conversation history is long, when the user sends a new message, then the UI sends a bounded conversation context to the backend (at most the last 12 messages; older context may be summarized, but any summary must be strictly bounded)."
  - "Given AI chat is disabled by server config, when a message is sent, then the UI shows a clear 'not enabled' response without crashing and without exposing provider details."
  - "Given AI chat is enabled, when a message is sent, then the backend streams an assistant reply over SSE and the UI renders the streamed content as a single assistant message in the conversation."
  - "Given the page is reloaded, when the user returns to the same tool (any version), then the conversation history is restored from IndexedDB (no server-side persistence)."
  - "Given the conversation history is long, then chat persistence is bounded (keep at most the most recent 200 messages and/or 1MB of UTF-8 text per {user_id, tool_id}; evict oldest first)."
  - "Given chat history is persisted, then full transcripts MUST NOT be stored in localStorage (localStorage is allowed only for small UI preferences such as Focus mode)."
  - "Given a message is sent, then the backend logs metadata only (template id, lengths, outcome) and never logs message text, prompts, or code."

dependencies:
  - "ST-08-18"
  - "ST-08-23"
  - "ST-14-31"
  - "ST-14-30"
ui_impact: "Yes (script editor drawer)"
data_impact: "No (no server-side persistence; client-side IndexedDB only)"
---

## Context

AI capabilities exist (ghost text + edit suggestions) but are not beginner-
friendly because they assume the author can
already start writing code and can select the right code region. We need a
chat-first entry point that guides novices and
organizes AI interactions in a single, predictable place.

## Notes

This story delivers the chat drawer UI + conversation state plumbing.

- Uses the streaming chat endpoint `POST /api/v1/editor/chat` (SSE)
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
  - Use IndexedDB via the same shared helper introduced in ST-14-30 (no
localStorage for full transcripts).
  - Scope keys by `{user_id, tool_id}`.
  - Persist `base_version_id` as metadata (not as part of the key).
  - Recommended TTL/cleanup: align with working copy head hygiene (e.g. expire
inactive threads after 30 days).
- Context sent to backend:
  - Always send a bounded tail (max 12 messages).
  - If implementing a rolling summary, it MUST be strictly bounded (e.g. ≤
1500 chars) and treated as optional context only.
- Layout:
  - Implement chat as an editor workspace drawer (reuse the existing right-
side drawer surface; do not introduce a second sidebar).
  - When opening chat in compare mode, enable Focus mode (ST-14-31) if it is
  not already enabled to preserve diff/editor legibility.
