---
type: pr
id: PR-0031
title: "Editor AI: patch-only edit-ops alignment (prompt + diff hygiene + correlation)"
status: ready
owners: "agents"
created: 2026-01-14
updated: 2026-01-14
stories:
  - "ST-08-24"
  - "ST-08-28"
tags: ["backend", "frontend", "editor", "ai", "diff", "observability", "prompt"]
links: ["PR-0015", "PR-0016", "PR-0021"]
acceptance_criteria:
  - "Edit-ops works without user cursor/selection targeting: the frontend omits both `selection` and `cursor` for edit-ops requests (v2 semantics) and the flow remains usable."
  - "The chat-ops system prompt makes `patch` the only allowed op; non-patch ops are treated as invalid and safe-fail with `ops=[]` and a user-actionable message."
  - "The system prompt includes explicit unified-diff validity rules (hunk mechanics) so the model reliably emits diffs the backend can apply."
  - "Backend patch preparation rejects or repairs malformed unified diffs (especially incorrect `@@ -a,b +c,d @@` counts) before calling subprocess `patch`, eliminating the common 'malformed patch' failure mode."
  - "A single `X-Correlation-ID` is propagated end-to-end across `edit-ops` → `preview` → `apply` so captures under `ARTIFACTS_ROOT/llm-captures/` match the correlation-id shown to users."
---

## Problem

Edit-ops v2 is patch-first, but the current contract and workflow still allow (and sometimes encourage) non-patch
operations and per-request correlation IDs. This causes:

- avoidable regeneration loops due to malformed unified diffs (e.g. wrong hunk header counts)
- confusion when the correlation-id shown to the user (edit-ops generation) does not match the correlation-id that fails
  (preview/apply)
- model ambiguity because the system prompt still documents multiple edit mechanisms

## Goal

Make edit-ops feel like a modern AI IDE workflow:

- patch-only output (single-file diffs per op; backend-first preview/apply; atomic undo)
- robust diff hygiene (normalize/repair predictable LLM mistakes)
- end-to-end correlation for fast diagnosis and reliable capture lookup

## Non-goals

- New editing capabilities (semantic refactors, multi-range edits, partial apply).
- Multi-file unified diffs in a single op (still rejected).
- Changing the bounded fuzz ladder policy (keep existing thresholds).
- Removing v1 CRUD op types from the protocol in this PR (follow-up cleanup if desired).

## Implementation plan

### 1) Patch-only system prompt (contract alignment)

- Update `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`:
  - Define `patch` as the only allowed operation type for edit-ops.
  - Add a short “unified diff validity checklist”:
    - hunk line prefixes (` `, `+`, `-`, `\\`)
    - `@@ -a,b +c,d @@` counts must match the hunk body line counts
    - single-file diffs only; canonical virtual file ids in headers

### 2) Backend enforcement (safe-fail for non-patch ops)

- In `src/skriptoteket/application/editor/edit_ops_handler.py`, add a final validation gate:
  - if any op is not `patch`, treat the proposal as invalid (return `ops=[]` + actionable assistant_message)
  - keep logging/capture metadata consistent (outcome should be clearly attributable)

### 3) Backend diff hygiene: patch lint + hunk header repair

- Extend `src/skriptoteket/infrastructure/editor/unified_diff_applier.py` in `prepare()`:
  - parse hunks and recompute old/new line counts from the hunk body
  - rewrite mismatched `@@ -a,b +c,d @@` counts (record normalization flag, e.g. `rewrote_hunk_counts`)
  - fail fast with a specific error for non-unified-diff lines inside hunks (prevents generic “Patchen kunde inte appliceras”)

- Add regression tests in `tests/unit/infrastructure/test_unified_diff_applier.py`:
  - captured malformed-count diff is repaired and becomes apply-able (or rejected with the specific error)

### 4) End-to-end correlation id propagation (edit-ops → preview → apply)

- Propagate the same `X-Correlation-ID` header on:
  - `POST /api/v1/editor/edit-ops`
  - `POST /api/v1/editor/edit-ops/preview`
  - `POST /api/v1/editor/edit-ops/apply`
- Target files:
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.spec.ts`

### 5) Stop sending selection/cursor for edit-ops requests (no “highlight-and-drag” requirement)

- Adjust edit-ops request composition to omit both `selection` and `cursor` for the edit-ops request.
- Keep preview/apply payloads consistent with the proposal (selection/cursor should remain omitted).
- Target files:
  - `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editOpsSelection.ts` (potentially unused after this change)

## Files touched (expected)

- Backend:
  - `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`
  - `src/skriptoteket/application/editor/edit_ops_handler.py`
  - `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`
  - `tests/unit/infrastructure/test_unified_diff_applier.py`
- Frontend:
  - `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.spec.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editOpsSelection.ts`

## Test plan

- Backend unit: `pdm run pytest tests/unit/infrastructure/test_unified_diff_applier.py -q`
- Frontend unit: `pdm run fe-test`
- Manual (dev):
  - Request edit-ops without selecting text → preview renders → apply works → undo works.
  - Confirm the same correlation-id is used for generation, preview failure, and apply failure.
  - Force a malformed hunk header (via capture replay) and confirm it is repaired or rejected with a specific error.

## Rollback plan

- Revert PR-0031. No migrations or data changes.
