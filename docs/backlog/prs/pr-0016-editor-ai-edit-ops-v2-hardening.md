---
type: pr
id: PR-0016
title: "Editor AI: edit-ops v2 hardening (backend patching + controlled fuzz + UX)"
status: ready
owners: "agents"
created: 2026-01-10
updated: 2026-01-10
stories:
  - "ST-08-24"
tags: ["backend", "frontend", "editor", "ai", "diff", "ux"]
acceptance_criteria:
  - "Backend supports preview/apply endpoints for edit-ops v2: `POST /api/v1/editor/edit-ops/preview` (no LLM calls) and `POST /api/v1/editor/edit-ops/apply` (version-gated by `base_hash` + `patch_id`, rejects with `409`)."
  - "Unified diffs are sanitized/normalized on the backend and applied using subprocess `patch` with a bounded fuzz ladder (0 → whitespace-tolerant strict → fuzz 1 → fuzz 2); multi-file diffs are rejected; applies are all-or-nothing."
  - "Frontend does not parse/apply diffs; it uses backend preview/apply and renders diffs from `before` vs `after_virtual_files`."
  - "If fuzz>0 OR max_offset>10, the UI shows a warning and requires an extra confirmation click before apply."
  - "Chat drawer keeps the prompt text until the edit-ops request succeeds (no silent prompt loss on failure)."
  - "Edit-ops request errors are visible in the chat UI (not only via toast) and are actionable."
  - "Patch/anchor preview+apply failures are surfaced clearly with a single Regenerate path; failures include compact hunk-level details when available."
  - "Selection requests include cursor at selection end per ADR-0051."
  - "Diff previews (AI proposal + working-copy restore modal) are height-constrained and scrollable; the close/action buttons remain reachable even for large diffs."
  - "After apply, the UI does not show a persistent banner that steals editor space; instead it exposes compact undo/redo controls and a clearly named restore point in “Öppna sparade”."
  - "When “Spara arbetsversion” is disabled, the save menu shows the specific blockers (schema errors, read-only, etc.)."
  - "Chat-ops timeout is tuned for local llama.cpp (slow generation is not treated as a failure)."
---

Related:
- Follow-up to `docs/backlog/prs/pr-0015-editor-ai-edit-ops-anchor-patch-v2.md`.
- Story: `docs/backlog/stories/story-08-24-ai-edit-ops-anchor-patch-v2.md`.
- ADR: `docs/adr/adr-0051-chat-first-ai-editing.md` (v2 request semantics + patch/anchor targeting).

## Problem

The v2 edit-ops flow exists, but there are trust-breaking gaps that prevent it from feeling “modern” (2026) and robust:

- Users can lose their drafted request when requesting edit-ops (chat drawer clears draft even on failure).
- Some failures are only visible via toast (easy to miss) and do not provide a single, clear “Regenerate” path.
- Patch application is still effectively strict client-side (regen loops) instead of using a controlled backend fuzz ladder.
- Missing backend wiring/entry points can break preview/apply (API route/model mapping must be correct).
- Diff previews can become unscrollable/overflow the viewport (AI diff panel + working-copy restore “Visa diff” modal).
- Post-apply UX can feel “stuck”: a banner encroaches editor space and “Spara arbetsversion” can be disabled without explaining why.

## Goal

Harden the edit-ops v2 pipeline end-to-end (backend patching + controlled fuzz + version-gated preview/apply + frontend
UX + tests) without expanding the feature scope. Reduce regen loops while keeping bounded safety and clear user control.

## Non-goals

- No new edit-ops capabilities (multi-range edits, semantic refactors).
- No multi-file patch apply (reject multi-file diffs).
- No partial apply: “all hunks or nothing” only.
- No new persistence tables/migrations.
- No new editor surface area beyond improving the existing chat + proposal + preview/apply flow.

## Implementation plan

1) **Confirm the patching strategy decisions (STOP and confirm with the user)**
   - Confirm patch apply engine: subprocess `patch` (not custom parsing).
   - Confirm confidence thresholds: hard-fail `max_offset > 50`; require confirmation when `fuzz>0 OR max_offset>10`.
   - Confirm validation split: relax model-level patch header strictness; sanitize/normalize on backend.

2) **Chat drawer UX**
   - Preserve the prompt draft until a request succeeds; restore on failure.
   - Ensure edit-ops request failures are visible in the chat drawer (SystemMessage).

3) **Backend-first preview/apply (version-gated)**
   - Add/verify `POST /api/v1/editor/edit-ops/preview` (no LLM calls) returning `after_virtual_files` + `meta`.
   - Add/verify `POST /api/v1/editor/edit-ops/apply` that re-runs preview and enforces `base_hash` + `patch_id` gating
     (reject with `409` and instruct user to re-preview + re-confirm).

4) **Patch sanitization + controlled fuzz ladder (backend)**
   - Implement a sanitization/normalization layer that strips predictable LLM noise (code fences, indentation, CRLF/LF,
     invisible chars) and standardizes headers to `--- a/<virtualFileId>` / `+++ b/<virtualFileId>`.
   - Reject multi-file diffs and any diff that targets a different file than `target_file`.
   - Apply using subprocess `patch` with stages: strict (fuzz 0) → whitespace-tolerant strict (`-l`) → fuzz 1 → fuzz 2.
   - Enforce confidence policy: hard-fail when `max_offset > 50`; surface `requires_confirmation` when `fuzz>0` OR
     `max_offset>10`.
   - Return actionable `error_details` (failed hunk header + compact snippets) on failure when possible.

5) **Frontend: server preview/apply + fuzz UX**
   - After `POST /api/v1/editor/edit-ops` returns ops, call preview endpoint to compute `after_virtual_files` and render
     diffs from `before` vs `after`.
   - Apply calls the backend apply endpoint with `base_hash` + `patch_id` from preview.
   - On `409`, force a re-preview and require explicit re-confirmation (never silently apply a rebased result).
   - Treat `requires_confirmation`/fuzz/offset as a safety signal: show a warning banner and require an extra click.
   - Remove/deprecate any client-side unified diff applier (frontend must not apply patches).

6) **Frontend: modern post-apply UX + scroll safety**
   - Ensure diff viewers are always height-constrained and scrollable (AI proposal diff + working-copy restore diff modal).
   - Replace the post-apply banner with compact undo/redo controls that do not steal CodeMirror real estate.
   - Ensure a clearly named restore point is created before apply so users can find it in “Öppna sparade”.
   - Show save blockers inline when “Spara arbetsversion” is disabled.

7) **Runtime support**
   - Ensure the backend runtime image has the `patch` binary available (install in Docker images used by dev/prod).

8) **Tests + verification**
   - Backend unit tests: sanitizer edge cases (fences/CRLF/missing headers), fuzz ladder, version gating, misapply-safe
     failures.
   - Frontend unit tests: draft retention, inline error visibility, preview/apply gating tokens, fuzz warning UX.
   - Add a minimal Playwright check to ensure large diffs don’t break scroll/close affordances.

## Checklist (MUST be kept updated during implementation)

### Decisions (confirmed by user on 2026-01-10)

- [x] Use subprocess `patch` as the unified diff applier (no custom diff parser).
- [x] Confidence thresholds: hard-fail `max_offset > 50`; require confirmation when `fuzz>0 OR max_offset>10`.
- [x] Relax model-level patch header validation; enforce/normalize headers in backend sanitization.

### Backend patching (preview/apply)

- [x] `POST /api/v1/editor/edit-ops/preview` applies ops on virtual files without calling the LLM.
- [x] `POST /api/v1/editor/edit-ops/apply` enforces `base_hash` + `patch_id` version gating (409 on mismatch).
- [x] Patch sanitizer strips fences/indentation/invisible chars, normalizes line endings, standardizes headers.
- [x] Multi-file diffs are rejected; partial apply is disallowed (all hunks or nothing).
- [x] Controlled ladder: strict → whitespace-tolerant strict → fuzz 1 → fuzz 2.
- [x] Confidence policy enforced: fail on `max_offset > 50`; `requires_confirmation` when `fuzz>0 OR max_offset>10`.
- [x] Failure details include hunk header + compact snippets when available (actionable regenerate).
- [x] Fix missing imports/undefined response models in `src/skriptoteket/web/api/v1/editor/edit_ops.py` (preview/apply).
- [x] Web layer converts `EditorEditOps*Op` models → dicts before building `EditOpsPreviewCommand`/`EditOpsApplyCommand` (prevents 500s).

### Frontend UX

- [x] Chat drawer: “Föreslå ändringar” does not clear draft until request succeeds.
- [x] Chat drawer: edit-ops request failures show via `SystemMessage` (and do not rely only on toast).
- [x] Edit-ops request uses cursor semantics aligned with ADR-0051 when selection exists (cursor defaults to selection end).
- [x] Proposal preview uses backend preview results (`after_virtual_files`) rather than client patch apply.
- [x] Apply uses backend apply with `base_hash` + `patch_id`; 409 triggers re-preview + re-confirm.
- [x] Fuzz/offset warning banner + extra confirmation click when `requires_confirmation=true`.
- [x] Client-side unified diff apply is removed/unused (`frontend/apps/skriptoteket/src/composables/editor/diff/applyUnifiedPatchStrict.ts`).
- [x] Diff previews are scroll-safe (AI proposal panel + working-copy restore modal “Visa diff”).
- [x] Post-apply UX is compact: toolbar “AI” pill + undo/redo mini-buttons (no persistent banner).
- [x] Restore-point label for AI apply is user-readable (“AI: före tillämpning”) and visible in “Öppna sparade”.
- [x] Save menu shows blockers when saving is disabled (schema errors/read-only/etc).

### Prompt/contract alignment

- [x] Prompt contract reinforces diff-only output (no markdown fences/prose), single-file diffs, and patch-first behavior.
- [x] Protocol validation does not reject patch headers that the backend sanitizer can normalize safely.

### Regression tests

- [x] `pdm run fe-test` (add/update tests near `editOps.spec.ts` / `useEditorEditOps.spec.ts`).
- [x] `pdm run pytest tests/unit/application/test_editor_edit_ops_handler.py -q`.
- [x] `pdm run pytest tests/unit/application/test_editor_edit_ops_preview_handler.py tests/unit/infrastructure/test_unified_diff_applier.py tests/unit/web/test_editor_edit_ops_preview_apply_api.py -q`.
- [x] `pdm run python -m scripts.playwright_st_08_24_working_copy_diff_scroll_check --base-url http://localhost:5173` (macOS escalation may be needed).

### Manual verification (record steps)

- [x] Manual: preview/apply endpoints (no LLM) via curl: preview/apply `200` + apply mismatch `409`.
- [ ] Manual: request edit without explicit location → proposal preview renders → apply works → undo works.
- [ ] Manual: trigger expected failure(s) (patch mismatch / anchor ambiguity / 409 conflict) → clear error + regenerate path.
- [ ] Manual: fuzz scenario triggers warning + extra confirm click (and is visible to the user).
- [x] Record exact commands + steps in `.agent/handoff.md`.

## Test plan

- `pdm run fe-test`
- `pdm run pytest tests/unit/application/test_editor_edit_ops_handler.py -q`
- Manual: open `/admin/tools/:toolId` → chat → request edit-ops → preview → apply → undo

## Rollback plan

Revert the PR. No migrations or data changes are introduced.
