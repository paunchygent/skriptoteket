---
type: story
id: ST-08-21
title: "AI: structured CRUD edit ops protocol v1 (insert/replace/delete)"
status: ready
owners: "agents"
created: 2026-01-01
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user requests an edit in chat, when the backend calls the LLM, then it requests a response in a strict, schema-validated edit-ops format (no markdown)."
  - "Given the LLM returns a valid response, when the backend parses it, then it returns a response containing a list of edit operations supporting insert/replace/delete against one of: whole document, selection, or cursor."
  - "Given the LLM returns invalid JSON or violates the schema, when the backend processes the response, then it fails safely with an empty operation list and a user-actionable message (no 500)."
  - "Given the upstream provider indicates truncation (finish_reason=length), when an edit is requested, then the backend returns an empty operation list (no partial edits)."
  - "Given the request is over budget, when an edit is requested, then the backend returns an empty operation list and exposes eval-only metadata (template id + outcome) when eval mode is enabled."
  - "Given an edit is requested, then the backend logs metadata only (no prompts, no code, no model output text)."
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
