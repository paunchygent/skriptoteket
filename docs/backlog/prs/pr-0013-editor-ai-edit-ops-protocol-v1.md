---
type: pr
id: PR-0013
title: "AI editor: structured edit-ops protocol v1 (ST-08-21)"
status: ready
owners: "agents"
created: 2026-01-09
updated: 2026-01-09
stories:
  - "ST-08-21"
adrs:
  - "ADR-0051"
  - "ADR-0052"
tags: ["backend", "editor", "ai", "llm"]
acceptance_criteria:
  - "POST /api/v1/editor/edit-ops accepts {tool_id, message, active_file, selection/cursor, virtual_files} and returns {enabled, assistant_message, ops, base_fingerprints}."
  - "Edit ops are schema-validated: op in {insert, replace, delete}; target in {document, selection, cursor}; target_file is a canonical virtual file id."
  - "Response includes base_fingerprints as sha256:<hex> over exact UTF-8 virtual file contents used for generation."
  - "Backend uses the canonical server-side chat thread (context editor_chat) for multi-turn context; it persists the newest user message and assistant response with metadata-only logging."
  - "Budgeting follows ADR-0052: never truncate the system prompt; drop oldest turns first; if prompt is over budget, return ops=[] with a user-actionable assistant_message and do not mutate stored chat state."
  - "Invalid JSON, schema violations, truncation, or upstream errors fail safely with ops=[] (no partial edits)."
  - "LLM_CHAT_OPS_* settings and prompt template are separate from LLM_CHAT_* and LLM_EDIT_*."
  - "Edit-ops requests share the chat in-flight guard (one chat/edit-ops request per user/tool at a time)."
---

## Problem

The current AI edit flow returns raw replacement text for a selected region, which is not compatible with the planned
chat-first UX and cannot safely express multi-file, structured edits. We need a backend protocol that can propose
validated CRUD operations across canonical virtual files and can be previewed/applied deterministically.

## Goal

Introduce a structured edit-ops API that consumes the canonical chat thread, validates JSON-only responses, and returns
deterministic ops + base fingerprints for downstream diff preview/apply (ST-08-22).

## Non-goals

- No diff preview/apply UI (ST-08-22).
- No new persistence tables; reuse the existing `tool_sessions` + `tool_session_messages` thread for context.
- No multi-range or pattern-based edit targets in v1.

## Implementation plan

1) **Contract + models**
   - Add Pydantic request/response models for `POST /api/v1/editor/edit-ops`.
   - Define op schema: `{op, target_file, target, content?}` with strict validation rules.
   - Define `base_fingerprints` as `{ [virtual_file_id]: "sha256:<hex>" }`.

2) **Prompt template**
   - Add a dedicated system prompt template (e.g. `editor_chat_ops_v1`) registered in
     `prompt_templates.py`.
   - Prompt must instruct JSON-only output matching the edit-ops schema (no markdown).

3) **Settings + budgeting**
   - Add `LLM_CHAT_OPS_*` settings (enabled flag, base URL, model, tokens, temp, timeouts, context window).
   - Add a budget helper for chat ops:
     - never truncate the system prompt
     - drop oldest chat turns first
     - do not truncate virtual files in v1
     - if newest message + full virtual files can’t fit, return ops=[] with a user-actionable message and **do not**
       mutate stored chat state.

4) **Provider + handler**
   - Create a non-streaming chat provider for edit-ops (OpenAI-compatible `/v1/chat/completions`).
   - Handler responsibilities:
     - require contributor role + tool access
     - load canonical thread (`context="editor_chat"`) and apply TTL rules
     - compose LLM request using prior chat + structured JSON payload with `virtual_files`
     - enforce prompt budget (ADR-0052)
     - parse JSON response → validate ops → compute fingerprints
     - safe-fail on invalid JSON/truncation/errors (ops=[] + assistant_message)
     - persist user + assistant messages in the canonical thread
   - Use the existing chat in-flight guard to prevent concurrent requests.

5) **Routing**
   - Add `POST /api/v1/editor/edit-ops` with thin web layer and CSRF enforcement.
   - Mirror `X-Skriptoteket-Eval` admin gating for eval metadata headers (dev-only).

6) **Tests**
   - Unit tests for handler:
     - disabled configuration
     - over-budget (no mutation)
     - invalid JSON / schema violations
     - truncated finish_reason
     - upstream error handling
     - base_fingerprints correctness
     - guard conflicts

## Test plan

- `pdm run pytest tests/unit/application/test_editor_edit_ops_handler.py -q`
- `pdm run pytest tests/unit/application -q`

## Rollback plan

Revert the PR. No migrations are introduced; the new endpoint can be removed without data loss.
