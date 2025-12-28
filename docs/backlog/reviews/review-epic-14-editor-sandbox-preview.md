---
type: review
id: REV-EPIC-14
title: "Review: Editor sandbox preview and draft locks"
status: approved
owners: "agents"
created: 2025-12-27
reviewer: "lead-developer"
epic: EPIC-14
adrs:
  - ADR-0044
  - ADR-0045
  - ADR-0046
stories:
  - ST-14-06
  - ST-14-07
  - ST-14-08
---

## TL;DR

This review evaluates the proposed implementation for IDE-like sandbox preview
runs (unsaved code and schemas), snapshot-stable next_actions, sandbox-only
settings, and per-tool draft head locks with admin/superuser override.

## Problem Statement

Tool authors need to experiment without saving drafts for every change, while
preventing concurrent edits from corrupting draft work. Sandbox settings must be
isolated from production settings and tied to the draft head so that preview
iterations are fast and safe.

## Proposed Solution

Adopt snapshot-based sandbox preview runs, require `snapshot_id` for next_actions,
store sandbox settings per user + draft head, and enforce draft head locks with
TTL heartbeat and force takeover for admins/superusers.

## Artifacts to Review

| File | Focus | Time |
| --- | --- | --- |
| `docs/reference/ref-editor-sandbox-preview-plan.md` | End-to-end plan and decisions | 20 min |
| `docs/backlog/epics/epic-14-admin-tool-authoring.md` | Epic scope alignment | 5 min |
| `docs/backlog/stories/story-14-03-sandbox-next-actions-parity.md` | Related behavior | 5 min |
| `docs/backlog/stories/story-14-04-sandbox-input-schema-form-preview.md` | Related behavior | 5 min |
| `docs/backlog/stories/story-14-05-editor-sandbox-settings-parity.md` | Baseline ACs | 5 min |

**Total estimated time:** ~40 minutes

## Key Decisions

| Decision | Rationale | Approve? |
| --- | --- | --- |
| Snapshot storage uses `sandbox_snapshots` table with TTL cleanup | Durable across restarts; clear lifecycle | [x] |
| Sandbox settings saved per user + draft head with schema hash | Isolated from production and stable for iteration | [x] |
| `snapshot_id` required for next_actions | Guarantees multi-step consistency | [x] |
| Draft head lock (TTL + heartbeat), admin/superuser force takeover | Prevents concurrent edits and allows override | [x] |

## Review Checklist

- [ ] Snapshot runs use unsaved editor payloads, not saved ToolVersion content
- [ ] `snapshot_id` is required for start-action and protects multi-step runs
- [ ] Sandbox settings do not affect production settings
- [ ] Lock enforcement blocks edits and preview for non-owners
- [ ] Admin/superuser override is explicit and logged
- [ ] DDD boundaries respected (UoW, DomainError, protocols)
- [ ] OpenAPI and TS types updated
- [ ] Test plan covers lock conflicts, snapshot expiry, and settings validation

## Final Review Task (post-implementation)

**Objective:** Validate the full feature end-to-end and catch low-level gaps in
implementation or architectural compliance before approval.

**Scope:** Backend handlers + repos + DB migrations, editor API contracts,
frontend editor/sandbox UI, and tests.

### Low-level gap checks

- [ ] `sandbox-settings` context stays <=64 chars and is collision-resistant.
- [ ] `snapshot_id` is persisted on tool runs and returned by run details.
- [ ] Sandbox session endpoint supports `snapshot_id` query param and uses
      `sandbox:{snapshot_id}` for preview runs.
- [ ] Draft head lock updates on save are atomic with draft head creation.
- [ ] Snapshot TTL cleanup exists (scheduled) and logs deleted counts.
- [ ] Snapshot payload size limits are enforced with clear validation errors.
- [ ] Start-action rejects missing/expired snapshot_id with actionable error.
- [ ] Lock enforcement covers preview run, start-action, sandbox settings
      resolve/save, and draft head saves.

### Architectural compliance checks

- [ ] Protocol-first DI: new repos and handlers depend on `Protocol`, not
      concrete implementations.
- [ ] UoW owns transactions; repositories do not commit.
- [ ] Domain stays pure (no HTTP errors); web layer maps DomainError → HTTP.
- [ ] `tool_sessions` context length enforcement honored everywhere.
- [ ] No legacy shims introduced; old paths removed if superseded.
- [ ] File sizes remain within 400–500 LOC guidance.

### UX/Behavior checks (manual or Playwright)

- [ ] Unsaved editor changes run correctly in sandbox preview.
- [ ] Next actions use the same snapshot after edits.
- [ ] Sandbox settings persist per user + draft head only.
- [ ] Lock UI is read-only for draft-head edits + sandbox, but metadata remains
      editable.
- [ ] Force takeover works for admin/superuser; previous holder loses access.

### Artifacts to review (post-implementation)

Backend:
- `src/skriptoteket/web/api/v1/editor.py`
- `src/skriptoteket/application/scripting/handlers/run_sandbox_preview.py` (new)
- `src/skriptoteket/application/scripting/handlers/start_sandbox_action.py`
- `src/skriptoteket/application/scripting/handlers/*sandbox_settings*.py` (new)
- `src/skriptoteket/application/scripting/handlers/*draft_lock*.py` (new)
- `src/skriptoteket/domain/scripting/*` (snapshot + lock helpers)
- `src/skriptoteket/protocols/*` (snapshot + lock protocols)
- `src/skriptoteket/di/scripting.py`
- `src/skriptoteket/infrastructure/db/models/*` (new tables + tool_run snapshot_id)
- `migrations/*` (snapshot + lock + tool_run changes)

Frontend:
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useToolVersionSettings.ts` (if replaced)
- `frontend/apps/skriptoteket/src/composables/editor/useSandboxSettings.ts` (new)

Tests:
- `tests/unit/application/scripting/handlers/*sandbox*.py`
- `scripts/playwright_st_14_0x_*.py` (if added)

### Verification commands

- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types`
- `pdm run docs-validate`

---

## Review Feedback

**Reviewer:** @gpt-5.2-pro
**Date:** 2025-12-27
**Verdict:** approved

### Required Changes

1. **Fix sandbox settings session context length (domain invariant violation)**
   - The proposed sandbox settings context format `sandbox-settings:{draft_head_id}:{schema_hash[:32]}` will exceed the current ToolSession `context` max length (64 chars) enforced in `src/skriptoteket/domain/scripting/tool_sessions.py`.
   - **Required:** revise `compute_sandbox_settings_session_context(...)` to produce a <=64 character context without weakening semantics (still “per user + draft head + schema variation”). Acceptable approaches include:
     - `sandbox-settings:{sha256(f"{draft_head_id}:{schema_hash}")[:32]}` (preferred; compact + collision-resistant), or
     - `sandbox-settings:{sha256(draft_head_id)[:14]}:{schema_hash[:32]}` (exactly 64 chars).
   - Update **REF plan**, **ADR-0045**, and **ST-14-08** to match the corrected context scheme.

2. **Define “draft head” semantics across locks/settings/snapshots**
   - “Draft head” is central to ADR-0046 / the REF plan, but lifecycle semantics are underspecified, especially when saving creates a new draft ToolVersion.
   - **Required:** explicitly define what `draft_head_id` refers to and what happens to existing locks when a save produces a new head (e.g., server migrates the lock row to the new head vs UI re-acquires lock). Ensure backend checks remain consistent after save.

3. **Enforce locks for all sandbox operations, including start-action**
   - The plan states preview/settings/save require an active lock, but enforcement must explicitly cover all sandbox flows.
   - **Required:** enforce and test lock ownership for:
     - sandbox preview run (`run_sandbox`)
     - sandbox start-action (`start_sandbox_action`)
     - sandbox settings resolve/save endpoints
     - editor save endpoints that mutate the draft head

4. **Resolve documentation contradictions with superseded acceptance criteria**
   - Existing ACs (ST-14-04/ST-14-05) that disable run/settings changes when “unsaved changes” exist conflict with the new snapshot preview direction (ST-14-06/08).
   - **Required:** update ST-14-04 and ST-14-05 to clearly supersede or revise those constraints.
   - Also reconcile the sandbox session context shift (e.g., legacy `sandbox:{version_id}` vs new `sandbox:{snapshot_id}`) across related docs (e.g., ST-14-03/ADR-0038) or explicitly state what is superseded.

5. **Specify the operational mechanism for TTL cleanup**
   - Snapshots are TTL-based, but the plan does not specify how cleanup runs operationally.
   - **Required:** add an explicit operational plan (scheduler mechanism, cadence, monitoring/logging, failure modes). If relying on opportunistic cleanup, state that clearly and justify it.

### Suggestions (Optional)

- Persist or recover `snapshot_id` linkage (e.g., store on ToolRun metadata or expose in run retrieval) to support UI reload/resume without forcing a rerun.
- Decide the fate of existing sandbox session endpoints: update to accept `snapshot_id` (query param or path) or deprecate to avoid semantic mismatch.
- Add payload size limits/validation for snapshot storage (code/schema/UI payload) to avoid unbounded DB growth under heavy iteration.
- Clarify what “read-only editor” disables in the UI and mirror that enforcement server-side (and document it).

### Decision Approvals

- [x] Snapshot storage
- [x] Sandbox settings isolation
- [x] Snapshot-stable next_actions
- [x] Draft head lock and override

---

## Changes Made

Required doc alignment updates are addressed; implementation changes remain
scoped to the sprint stories.

| Change | Artifact | Description |
| --- | --- | --- |
| 1 | REF-editor-sandbox-preview-plan | Added draft head semantics, lock enforcement list, TTL cleanup ops, payload limits, snapshot_id in run details, session endpoint snapshot_id param, and read-only scope. |
| 2 | ADR-0045 | Updated sandbox settings context to hashed <=64 format. |
| 3 | ST-14-08 | Updated context formula and lock enforcement for sandbox settings. |
| 4 | ADR-0046 | Defined draft head semantics, lock update on save, and lock scope. |
| 5 | ST-14-07 | Added lock update-on-save acceptance criteria and clarified read-only scope. |
| 6 | ST-14-06 | Clarified lock enforcement in acceptance criteria (snapshot_id recovery already present). |
| 7 | ST-14-04 / ST-14-05 | Revised ACs to align with snapshot preview behavior (removed dirty-state blocks). |
| 8 | ADR-0038 / ST-14-03 | Added pre-snapshot notes; snapshot-scoped context will be enforced by ST-14-06 / ADR-0044. |
| 9 | ADR-0044 | Added TTL cleanup ops and snapshot_id in run details. |
