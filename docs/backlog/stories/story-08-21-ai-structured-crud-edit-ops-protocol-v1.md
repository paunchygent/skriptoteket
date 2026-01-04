---
type: story
id: ST-08-21
title: "AI: structured CRUD edit ops protocol v1 (insert/replace/delete)"
status: ready
owners: "agents"
created: 2026-01-01
updated: 2026-01-04
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user requests an edit in chat, when the frontend calls `POST /
api/v1/editor/edit-ops`, then the backend requests a response in a strict,
schema-validated edit-ops format (JSON only; no markdown)."
  - "Given an edit-ops request is sent, then the request includes the
canonical virtual_files payload (tool.py, entrypoint.txt,
settings_schema.json, input_schema.json, usage_instructions.md) and a bounded
conversation context so proposals are deterministic and previewable."
  - "Given the LLM returns a valid response, when the backend parses it, then
it returns `{ enabled: true, assistant_message: string, ops: [...] }` where
each op supports insert/replace/delete against one of: whole document,
selection, or cursor, and each op targets an explicit virtual file from the
canonical editor file map: tool.py, entrypoint.txt, settings_schema.json,
input_schema.json, usage_instructions.md."
  - "Given the backend returns an edit-ops proposal, then the response
includes `base_fingerprints` per virtual file so the frontend can detect stale
proposals reliably (ST-08-22)."
  - "Given base_fingerprints are returned, then each fingerprint is
`sha256:<hex>` computed over the exact UTF-8 content of the corresponding
virtual file used as the base (no normalization)."
  - "Given edit-ops is disabled by server config, when the frontend calls
`POST /api/v1/editor/edit-ops`, then the backend returns `enabled=false` with
an empty operation list and a user-actionable message (no 500, no provider
details)."
  - "Given the LLM returns invalid JSON or violates the schema, when the
backend processes the response, then it fails safely with an empty operation
list and a user-actionable message (no 500)."
  - "Given the upstream provider indicates truncation (finish_reason=length),
when an edit is requested, then the backend returns an empty operation list
(no partial edits)."
  - "Given the request is over budget, when an edit is requested, then the
backend returns an empty operation list and exposes eval-only metadata
(template id + outcome) when eval mode is enabled."
  - "Given an edit is requested, then the backend logs metadata only (no
prompts, no code, no model output text)."
  - "Given edit-ops is configured, then it uses a dedicated `LLM_CHAT_OPS_*`
profile (does not reuse `LLM_COMPLETION_*` and does not reuse the legacy
`LLM_EDIT_*` prompts)."
dependencies:
  - "ST-08-18"
  - "ST-08-20"
  - "ST-14-17"
ui_impact: "Yes (enables chat-driven edit proposals)"
data_impact: "No (stateless requests)"
---

## Context

ST-08-16 returns raw replacement text. To support a chat-first CRUD experience
with deterministic previews, we need the
LLM to return structured operations that can be validated, previewed, and
applied in a controlled way.

## Notes

- Targets are intentionally limited in v1 to keep edits deterministic and
  safe: whole document, current selection, or
    cursor insertion.
- More advanced targeting (multi-range edits, pattern/anchor-based edits,
  protected regions) is deferred to follow-ups.

- This story assumes the editor provides the LLM with a set of named **virtual
  files** (separate logical documents) so
    the assistant can “see both” code + schemas while respecting boundaries. The
  UI may still present a combined “Pro mode”
    buffer, but edit operations should target virtual files explicitly to keep
    edits safe and predictable.
  - Canonical names match the diff viewer map in ST-14-17 to keep preview/
    apply consistent.

- Response envelope should include both `assistant_message` (for the chat
  transcript) and `ops[]` (for preview/apply).
- Safe-fail rule: invalid JSON/schema, truncation (`finish_reason=length`), or
  over-budget responses must return
    `ops=[]` (no partial apply).

See also:

- Chat drawer UX (producer of requests): `docs/backlog/stories/story-08-20-
editor-ai-chat-drawer-mvp.md`
- Diff preview/apply (consumer of response): `docs/backlog/stories/story-08-
22-editor-ai-diff-preview-apply-undo.md`
- Canonical virtual file ids: `docs/backlog/stories/story-14-17-editor-
version-diff-view.md`

## Protocol contract (v1)

### Canonical virtual file ids

- `tool.py`
- `entrypoint.txt`
- `settings_schema.json`
- `input_schema.json`
- `usage_instructions.md`

These ids are canonical across:

- ST-14-17 (diff tabs + patch pseudo-paths)
- ST-14-18 (`field=` deep links)
- ST-08-21 (edit-ops `target_file`)
- ST-08-22 (diff preview)

### Request payload (frontend → backend)

`POST /api/v1/editor/edit-ops` MUST include:

- `tool_id` (UUID; for permission checks + metadata logging)
- `instruction` (string; the user’s current request)
- `conversation` (bounded list; max length enforced by the frontend)
- `active_file` (one of the canonical virtual file ids)
- `selection` (optional) and/or `cursor` (optional), so v1 targeting is well-
defined:
  - selection: `{ from: int, to: int }` in the active file
  - cursor: `{ pos: int }` in the active file
- `virtual_files`: a map containing the full current text for each canonical
virtual file id

### Response payload (backend → frontend)

Backend returns:

- `enabled: bool`
- `assistant_message: string` (may be empty; used in the chat transcript)
- `ops: []` (empty on any safe-fail condition)
- `base_fingerprints: { [virtual_file_id]: "sha256:<hex>" }`

### Fingerprint algorithm (explicit)

- `base_fingerprints[virtual_file_id]` MUST be computed as `sha256` over the
  exact UTF-8 bytes of
    `virtual_files[virtual_file_id]` as used during proposal generation.
- No normalization (no trimming, no newline conversion).
