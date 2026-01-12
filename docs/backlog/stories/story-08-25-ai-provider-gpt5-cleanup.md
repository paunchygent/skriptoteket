---
type: story
id: ST-08-25
title: "AI: remove legacy edit suggestions + GPT-5 config support"
status: done
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
epic: "EPIC-08"
acceptance_criteria:
  - "Given a caller requests the legacy edit suggestions endpoint `POST /api/v1/editor/edits`, when the request is made, then the route is not available (and is removed from the exported OpenAPI schema)."
  - "Given the SPA codebase, when building or testing, then there is no dead UI/client code for the removed edit suggestions flow (no `EditorEditSuggestionPanel.vue`, no `useEditorEditSuggestions`, no `/api/v1/editor/edits` usage)."
  - "Given `LLM_COMPLETION_MODEL=gpt-5-nano` and `LLM_COMPLETION_REASONING_EFFORT=minimal`, when the backend calls the OpenAI-compatible `/v1/chat/completions` endpoint, then it sends `max_completion_tokens` and `reasoning_effort` and does not send `max_tokens` or `temperature`."
  - "Given `LLM_CHAT_MODEL=gpt-5.2` and `LLM_CHAT_REASONING_EFFORT=low`, when the backend calls the OpenAI-compatible `/v1/chat/completions` endpoint, then it sends `max_completion_tokens` and `reasoning_effort` and does not send `max_tokens` or `temperature`."
  - "Given `LLM_CHAT_OPS_MODEL=gpt-5.2` and `LLM_CHAT_OPS_REASONING_EFFORT=low`, when the backend calls the OpenAI-compatible `/v1/chat/completions` endpoint, then it sends `max_completion_tokens` and `reasoning_effort` and does not send `max_tokens` or `temperature`."
  - "Given the LLM base URL points to a local llama-server (`http://localhost:8082`), when calling chat completions, then the backend continues to use `max_tokens` + `temperature` and does not send `reasoning_effort`."
ui_impact: "No (removes unused component only)"
data_impact: "No"
dependencies:
  - "ADR-0043"
  - "ADR-0051"
---

## Context

We have two competing edit surfaces:

- Legacy “edit suggestion” (single replacement text) over `POST /api/v1/editor/edits` (LLM_EDIT_* profile).
- Chat-first edit ops (ADR-0051) over `POST /api/v1/editor/edit-ops` (LLM_CHAT_OPS_* profile).

The edit suggestion UI component is not wired into the SPA routes, and the legacy endpoint creates confusion.
At the same time, we want a tiered OpenAI setup using GPT-5 models with `reasoning_effort` and
`max_completion_tokens`, and we must not send unsupported sampling params to GPT-5-family models.

## Scope

- Remove the legacy edit suggestion endpoint and related dead UI/client code.
- Add config fields for `reasoning_effort` per profile and ensure GPT-5 model requests use
  `max_completion_tokens` and include `reasoning_effort`.
