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
  - "Given the user writes a message and presses Send, when the request is in flight, then the UI shows a clear loading state and prevents duplicate sends."
  - "Given AI chat is disabled by server config, when a message is sent, then the UI shows a clear 'not enabled' response without crashing and without exposing provider details."
  - "Given AI chat is enabled, when a message is sent, then the backend returns an assistant reply and the UI renders it as a message in the conversation."
  - "Given the page is reloaded, when the user returns to the same tool/version, then the conversation history is restored from local storage (no server-side persistence)."
  - "Given a message is sent, then the backend logs metadata only (template id, lengths, outcome) and never logs message text, prompts, or code."
dependencies:
  - "ST-08-18"
ui_impact: "Yes (script editor drawer)"
data_impact: "No (no server-side persistence; local storage only)"
---

## Context

AI capabilities exist (ghost text + edit suggestions) but are not beginner-friendly because they assume the author can
already start writing and can select the right code region. We need a chat-first entry point that guides novices and
organizes AI interactions in a single, predictable place.

## Notes

This story delivers the chat drawer UI + conversation state plumbing. Structured edit operations, diff preview, and
apply/undo are handled in follow-up stories.
