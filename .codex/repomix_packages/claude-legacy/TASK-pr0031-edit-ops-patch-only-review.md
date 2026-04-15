# External Review: Proposed PR-0031 — Editor AI patch-only edit-ops

## Context Package

**Primary (includes PR + capture samples)**: `repomix-pr0031-edit-ops-patch-only-review-with-captures.xml` (48,008 tokens, 20 files)

Representative failure captures (included in the package):
- `.artifacts/llm-captures/edit_ops_preview_failure/7ea68185-a911-4661-9010-a41001927bca/capture.json`
- `.artifacts/llm-captures/edit_ops_preview_failure/fa4dd606-2400-485d-8095-71114dc63f6a/capture.json`

Optional larger code-first packs (if needed):
- `repomix-editor-ai-edit-ops-patch-only-review.xml`
- `repomix-editor-ai-edit-ops-patch-only-review-extended.xml`
- `repomix-editor-ai-edit-ops-patch-only-review-full.xml`

## Objective

Review the suggested implementation plan for tightening Skriptoteket’s edit-ops pipeline toward **“patch is what users expect”**:

1. Edit-ops requests work without cursor/selection; UI never requires selection gestures.
2. Model is instructed to output **patch ops only**, and backend safe-fails any non-patch ops.
3. Prompt explicitly requires **valid unified diffs** (and documents the exact validity rules).
4. Backend normalizes/repairs common LLM diff format errors (esp. wrong `@@ -a,b +c,d @@` counts) before invoking patch.
5. A single `X-Correlation-ID` is stable across **edit-ops → preview → apply** so captures/logs correlate to one id.

## What to Review (focus areas)

- **Contract design**: Is “patch-only” the right canonical edit-ops contract? Any remaining selection/cursor semantics that would keep the UX implicitly selection-dependent?
- **Backend enforcement**: Where should “patch-only” be enforced (parser vs handler) and what’s the safest failure mode (user message, `ops=[]`, error details)?
- **Unified diff validity + repair**:
  - Are the proposed “diff validity checklist” rules correct and unambiguous?
  - Is rewriting hunk header counts safe and deterministic?
  - Edge cases: multiple hunks, `\\ No newline at end of file`, empty hunks, weird prefixes, multi-file diffs.
- **Correlation propagation**:
  - Is it correct to reuse the *generation* correlation id for preview/apply?
  - Are there any other requests in the flow that should share the same id (e.g., undo/redo)?
- **Observability and capture-on-error**: Does the existing capture design (ST-08-28) align with the “stable, already propagated” expectation once frontend propagates the header?

## Suggested Implementation Touchpoints (as packaged)

### Backend

- Prompt contract: `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`
- Edit-ops handler / validation: `src/skriptoteket/application/editor/edit_ops_handler.py`
- Preview/apply handlers: `src/skriptoteket/application/editor/edit_ops_preview_handler.py`
- Diff engine (prepare/normalize/apply): `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`
- Correlation plumbing: `src/skriptoteket/web/middleware/correlation.py`, `src/skriptoteket/web/request_metadata.py`
- Capture store: `src/skriptoteket/infrastructure/llm/capture_store.py`

### Frontend

- Edit-ops state + request orchestration: `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
- Selection resolver (candidate for deprecation if unused): `frontend/apps/skriptoteket/src/composables/editor/editOps/editOpsSelection.ts`
- API client (add correlation header to preview/apply): `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`
- API tests: `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.spec.ts`

### Tests (backend)

- Diff applier: `tests/unit/infrastructure/test_unified_diff_applier.py`
- Edit-ops handler: `tests/unit/application/test_editor_edit_ops_handler.py`
- Preview/apply behavior: `tests/unit/application/test_editor_edit_ops_preview_handler.py`
- Capture-on-error: `tests/unit/application/test_editor_edit_ops_capture_on_error.py`, `tests/unit/application/test_editor_edit_ops_preview_capture_on_error.py`
- API contract: `tests/unit/web/test_editor_edit_ops_preview_apply_api.py`

### Docs (context)

- ST-08-24 (v2 patch-based edit-ops), ST-08-28 (capture-on-error), ST-07-01 (correlation IDs)
- Prior PR docs (v1 protocol, v2 patch/anchor, v2 hardening, capture-on-error, UX changes)
- ADRs describing the editor AI architecture and prompt budgeting decisions

## Deliverable from Reviewer

- A short written review covering: correctness, safety/UX implications, edge cases, and whether the proposed architecture changes match the acceptance criteria 1–5.
