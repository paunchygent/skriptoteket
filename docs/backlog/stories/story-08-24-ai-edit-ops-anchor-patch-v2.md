---
type: story
id: ST-08-24
title: "AI edit ops v2: anchor/patch-based targets + apply"
status: done
owners: "agents"
created: 2026-01-10
updated: 2026-01-11
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user requests an edit without explicitly targeting a location (the frontend omits both `selection` and `cursor`), when the frontend calls `POST /api/v1/editor/edit-ops`, then the backend instructs the model to return patch/anchor-based ops (no cursor-only insert ops)."
  - "Given the user has a selection in the active file, when the frontend calls `POST /api/v1/editor/edit-ops`, then it includes both `selection` and `cursor` (cursor position is explicitly defined; default to selection end) so cursor-target ops are always resolvable."
  - "Given an edit-ops response includes a `patch` op, when the frontend previews or applies it, then the backend sanitizes/normalizes the diff and applies it with a bounded fuzz ladder (0 → whitespace-tolerant strict → fuzz 1 → fuzz 2); unsafe/stale applies block apply with a regenerate message."
  - "Given an edit-ops response includes an `anchor` target, when the frontend previews or applies it, then the anchor must match exactly once in the base file or the proposal is rejected with a user-actionable error."
  - "Given a valid patch/anchor proposal across multiple virtual files, when the user clicks Apply, then all changes are applied atomically and can be undone as one change (same behavior as ST-08-22)."
  - "Given the patch/anchor payload is invalid or references non-canonical virtual files, when the backend processes the response, then it fails safely with `ops=[]` and a user-actionable assistant_message."
  - "Given an AI proposal is previewed, then the UI uses an AI-specific diff preview surface (reuse diff engine/capabilities, but not the full version-review diff UI chrome)."

dependencies:
  - "ST-08-21"
  - "ST-08-22"
  - "ST-14-17"
  - "ADR-0051"

ui_impact: "Yes (preview/apply uses patch/anchor targeting)"
data_impact: "No (protocol change only)"
---

## Context

Cursor/selection-only edit ops produce surprising inserts when the user has not
explicitly placed a cursor or selected a region. Coding assistants are expected
to locate edits by context (anchors) or patch hunks. We need a v2 edit-ops
contract that supports deterministic patch/anchor targeting without relying on
cursor position.

## Notes

- Patch ops use unified diffs with canonical virtual file ids.
- Anchor targets are strict (exact, single match) to prevent ambiguous edits.
- Reuse the existing preview/apply/undo capabilities (ST-08-22), but render diffs in an AI-specific view (minimal,
  no patch/copy/download UI intended for version review).

Related PRs:

- `docs/backlog/prs/pr-0015-editor-ai-edit-ops-anchor-patch-v2.md`
- `docs/backlog/prs/pr-0016-editor-ai-edit-ops-v2-hardening.md`
