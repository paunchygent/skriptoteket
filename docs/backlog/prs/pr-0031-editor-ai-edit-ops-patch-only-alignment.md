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

## Confirmed root causes (as of 2026-01-14)

### 1) Correlation-id instability (deterministic)

The frontend currently generates and uses a correlation id only for edit-ops generation, but does not propagate it to
preview/apply:

- `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`
  - `requestEditOps(...)` sets `headers: { "X-Correlation-ID": params.correlationId }`
  - `previewEditOps(...)` does **not** set `X-Correlation-ID`
  - `applyEditOps(...)` does **not** set `X-Correlation-ID`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
  - a `correlationId` is created and stored on the proposal for the request
  - `previewEditOps(...)` and `applyEditOps(...)` are called without passing that correlation id

Backend behavior is consistent with this:

- `src/skriptoteket/web/middleware/correlation.py` generates a new correlation id per request unless the header is
  provided.
- `src/skriptoteket/web/api/v1/editor/edit_ops.py` appends `correlation-id: <id>` to preview/apply errors based on the
  *request* correlation id.

Result: the correlation-id shown in the UI after generation cannot be used to locate preview/apply failures/captures.

### 2) Malformed unified diffs are not repaired; hunk counts are not validated

In `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`:

- `prepare(...)` normalizes (BOM/invisible chars/CRLF/code fences/indentation), standardizes headers, rejects multi-file
  diffs, ensures trailing newline, and parses hunks by scanning `@@` headers.
- `_parse_hunks(...)` extracts `old_start`, `old_count`, `new_start`, `new_count` from the hunk header, but does not
  verify that the counts match the hunk body.
- In `apply(...)`, the implementation relies on the system `patch` binary and parses output lines containing `Hunk #` to
  determine offsets/fuzz/failure hunk. If patch fails earlier with output like `malformed patch at line ...` (common
  with incorrect header counts), there will be no hunk-level parse signal, and the fallback message becomes the generic:
  `Patchen kunde inte appliceras. Regenerera.`

Representative failure captures (local):

- `.artifacts/llm-captures/edit_ops_preview_failure/7ea68185-a911-4661-9010-a41001927bca/capture.json`
- `.artifacts/llm-captures/edit_ops_preview_failure/fa4dd606-2400-485d-8095-71114dc63f6a/capture.json`

## Alignment with ADR-0051 / ST-08-24 / ST-08-28

- ADR-0051 / ST-08-24 (v2 semantics) explicitly requires that when selection/cursor are omitted, v2 is triggered by
  request semantics and patch/anchor targeting is used; cursor-only ops must safe-fail.
- Patch-only in v2 mode (when selection/cursor omitted) is consistent with ADR-0051 language (“patch and/or anchor”) and
  reduces variability.
- Patch-only *always* is a larger behavioral shift because ADR-0051 still documents CRUD ops as v1. If we choose “patch
  always”, ADR-0051 must be updated to avoid spec drift (or explicitly mark CRUD ops as supported-but-not-emitted).
- ST-08-28 expects captures keyed by correlation id (“stable, already propagated”). This is currently true per request,
  but not across the 3-request workflow; correlation propagation is required to meet the intent end-to-end.

## Reviewer requirements (minimum for approval)

### A) Include PR + capture artifacts in the review packet

- `docs/backlog/prs/pr-0031-editor-ai-edit-ops-patch-only-alignment.md` (this doc)
- Representative capture samples showing malformed hunks:
  - `.artifacts/llm-captures/edit_ops_preview_failure/7ea68185-a911-4661-9010-a41001927bca/capture.json`
  - `.artifacts/llm-captures/edit_ops_preview_failure/fa4dd606-2400-485d-8095-71114dc63f6a/capture.json`

### B) Fix correlation propagation across generation → preview → apply

Files:

- `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
- `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`

Options:

- **Option 1 (recommended): explicit plumbing via API params**
  - Extend `previewEditOps` and `applyEditOps` to accept `correlationId`
  - Set `X-Correlation-ID` in both requests
  - Pass `proposal.correlationId` from `useEditorEditOps.ts`
  - Pros: minimal, explicit, testable; avoids leaking correlation ids into unrelated requests
- Option 2: correlation-aware wrapper in `apiFetch` (risk: hidden coupling and accidental leakage)
- Option 3: backend-generated workflow id (bigger protocol change; diverges from “same X-Correlation-ID across calls”)

Non-negotiable acceptance check:

- Same `X-Correlation-ID` visible in edit-ops generation response, preview response, and apply response.

### C) Implement diff hygiene for malformed @@ headers

File:

- `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`

Must address the “incorrect `@@ -a,b +c,d @@` counts” failure mode.

Options:

- Option 1: repair hunk counts during `prepare()` (best UX; must be careful)
- Option 2: strict validation + actionable failure (safest; more regen loops)
- **Option 3 (recommended): hybrid**
  - attempt repair only when:
    - hunk body lines are syntactically valid (` ` | `+` | `-` | `\\`)
    - repair is purely count correction (do not rewrite body)
  - otherwise fail early with a specific, user-actionable error

Also required:

- When `patch` output indicates formatting errors without `Hunk #` lines (e.g. contains `malformed patch` / `at line`),
  map to a specific error such as:
  - “Diffen är felaktigt formaterad (ogiltig @@-hunk). Regenerera.”

### D) Make “patch-only” unambiguous and enforceable

Files:

- `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`
- `src/skriptoteket/application/editor/edit_ops_handler.py` (defensive validation)

Define what “patch-only” means and make it enforceable (prompt + backend validator).

Options:

- Option 1: patch-only always (strongest alignment with AI IDE diff workflows; requires ADR-0051 update)
- **Option 2: patch-only in v2 mode (recommended for minimal ADR impact)**
  - when selection/cursor are omitted: require `patch` ops only (reject CRUD ops, even with anchor)
  - when selection/cursor are present: keep existing behavior for v1 CRUD ops (until protocol cleanup)
- Option 3: prompt-only “prefer patch” (not acceptable alone; not deterministic)

### E) Add regression tests that prove the fixes

Diff hygiene:

- Add unit tests in `tests/unit/infrastructure/test_unified_diff_applier.py`:
  - mismatched hunk counts but syntactically valid body → repaired in `prepare()` and applies cleanly
  - unrecoverably malformed diff → specific error (not generic “Patchen kunde inte appliceras”)

Correlation propagation:

- Frontend test(s) verifying `X-Correlation-ID` is included on preview/apply and matches the proposal id (or explicitly
  document a manual verification step that checks request headers in DevTools and matches server logs).

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
