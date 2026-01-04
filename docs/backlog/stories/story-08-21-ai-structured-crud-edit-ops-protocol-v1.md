---
type: story
id: ST-08-21
title: "AI: structured CRUD edit ops protocol v1 (insert/replace/delete)"
status: ready
owners: "agents"
created: 2026-01-01
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user requests an edit in chat, when the frontend calls `POST /api/v1/editor/edit-ops`, then the backend requests a response in a strict, schema-validated edit-ops format (JSON only; no markdown)."
  - "Given the LLM returns a valid response, when the backend parses it, then it returns `{ enabled: true, assistant_message: string, ops: [...] }` where each op supports insert/replace/delete against one of: whole document, selection, or cursor, and each op targets an explicit virtual file (e.g. tool.py, input_schema.json, settings_schema.json)."
  - "Given the backend returns an edit-ops proposal, then the response includes `base_fingerprints` per virtual file so the frontend can detect stale proposals reliably (ST-08-22)."
  - "Given edit-ops is disabled by server config, when the frontend calls `POST /api/v1/editor/edit-ops`, then the backend returns `enabled=false` with an empty operation list and a user-actionable message (no 500, no provider details)."
  - "Given the LLM returns invalid JSON or violates the schema, when the backend processes the response, then it fails safely with an empty operation list and a user-actionable message (no 500)."
  - "Given the upstream provider indicates truncation (finish_reason=length), when an edit is requested, then the backend returns an empty operation list (no partial edits)."
  - "Given the request is over budget, when an edit is requested, then the backend returns an empty operation list and exposes eval-only metadata (template id + outcome) when eval mode is enabled."
  - "Given an edit is requested, then the backend logs metadata only (no prompts, no code, no model output text)."
  - "Given edit-ops is configured, then it uses a dedicated `LLM_CHAT_OPS_*` profile (does not reuse `LLM_COMPLETION_*` and does not reuse the legacy `LLM_EDIT_*` prompts)."
dependencies:
  - "ST-08-18"
  - "ST-08-20"
ui_impact: "Yes (enables chat-driven edit proposals)"
data_impact: "No (stateless requests)"
---

## Context

ST-08-16 returns raw replacement text. To support a chat-first CRUD experience with deterministic previews, we need the
LLM to return structured operations that can be validated, previewed, and applied in a controlled way.

## Notes

- Targets are intentionally limited in v1 to keep edits deterministic and safe: whole document, current selection, or
  cursor insertion.
- More advanced targeting (multi-range edits, pattern/anchor-based edits, protected regions) is deferred to follow-ups.

- This story assumes the editor provides the LLM with a set of named **virtual files** (separate logical documents) so
  the assistant can “see both” code + schemas while respecting boundaries. The UI may still present a combined “Pro mode”
  buffer, but edit operations should target virtual files explicitly to keep edits safe and predictable.

- Response envelope should include both `assistant_message` (for the chat transcript) and `ops[]` (for preview/apply).
- Safe-fail rule: invalid JSON/schema, truncation (`finish_reason=length`), or over-budget responses must return
  `ops=[]` (no partial apply).
- `base_fingerprints` should be stable and explicit (e.g. `sha256:<hex>` per virtual file content used as the base for
  proposal generation).
