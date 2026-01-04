---
type: story
id: ST-08-20
title: "Editor: AI chat drawer MVP (beginner-friendly assistant UI)"
status: ready
owners: "agents"
created: 2026-01-01
epic: "EPIC-08"
acceptance_criteria:
  - "Given a tool author is in the script editor, when they open the AI drawer, then a chat UI is shown without navigating away from the editor."
  - "Given the user writes a message and presses Send, when the request is in flight, then the UI prevents duplicate sends and shows a clear streaming state."
  - "Given an assistant reply is streaming, when the user clicks Cancel, then the stream stops immediately and the UI does not get stuck in a loading state."
  - "Given the conversation history is long, when the user sends a new message, then the UI only sends a bounded conversation context (e.g. last N turns and/or a rolling summary) to the backend."
  - "Given AI chat is disabled by server config, when a message is sent, then the UI shows a clear 'not enabled' response without crashing and without exposing provider details."
  - "Given AI chat is enabled, when a message is sent, then the backend streams an assistant reply over SSE and the UI renders the streamed content as a single assistant message in the conversation."
  - "Given the page is reloaded, when the user returns to the same tool (any version), then the conversation history is restored from IndexedDB (no server-side persistence)."
  - "Given the conversation history is long, then chat persistence is bounded (e.g. keep the most recent N messages) and does not rely on localStorage for large payloads."
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

AI capabilities exist (ghost text + edit suggestions) but are not beginner-friendly because they assume the author can
already start writing and can select the right code region. We need a chat-first entry point that guides novices and
organizes AI interactions in a single, predictable place.

## Notes

This story delivers the chat drawer UI + conversation state plumbing.

- Uses the streaming chat endpoint `POST /api/v1/editor/chat` (SSE) (implemented in ST-08-23).
- Non-goal: change inline completions (ghost text) behavior or prompt profiles (`POST /api/v1/editor/completions`).
- Structured edit operations, diff preview, and apply/undo are handled in follow-up stories (ST-08-21/22).
- **Decided persistence keying:** conversation history is keyed by `{user_id, tool_id}`; store `base_version_id` as metadata inside the stored payload (not in the key) so editor saves/new versions do not reset the chat.

## Implementation decisions

- Storage:
  - Use IndexedDB via the same `idb` helper introduced in ST-14-30 (no localStorage for full transcripts).
  - Scope keys by `{user_id, tool_id}`.
  - Persist `base_version_id` as metadata (not as part of the key).
- Layout:
  - Implement chat as an editor workspace drawer (reuse the existing right-side drawer surface; do not introduce a second sidebar).
  - When opening chat in compare mode, enable Focus mode (ST-14-31) if it is not already enabled to preserve diff/editor legibility.
