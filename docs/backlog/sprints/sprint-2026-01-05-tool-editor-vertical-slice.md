---
type: sprint
id: SPR-2026-01-05
title: "Sprint 2026-01-05: Tool editor vertical slice"
status: done
owners: "agents"
created: 2025-12-27
updated: 2025-12-31
starts: 2025-12-25
ends: 2026-01-01
objective: "Ship editor sandbox preview + draft locking + settings isolation so authors can iterate safely without publishing."
prd: "PRD-editor-sandbox-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-03", "ST-14-04", "ST-14-05", "ST-14-06", "ST-14-07", "ST-14-08"]
adrs: ["ADR-0038", "ADR-0044", "ADR-0045", "ADR-0046"]
---

## Objective

Deliver the editor sandbox vertical slice: snapshot-based preview runs, draft head
locks, sandbox-only settings, and parity for next_actions + input forms so
authors can iterate on drafts without publishing.

## Scope (committed stories)

- [ST-14-03: Editor sandbox next_actions parity](../stories/story-14-03-sandbox-next-actions-parity.md)
- [ST-14-04: Editor sandbox input_schema form preview](../stories/story-14-04-sandbox-input-schema-form-preview.md)
- [ST-14-05: Editor sandbox settings parity](../stories/story-14-05-editor-sandbox-settings-parity.md)
- [ST-14-06: Editor sandbox preview snapshots](../stories/story-14-06-editor-sandbox-preview-snapshots.md)
- [ST-14-07: Editor draft head locks](../stories/story-14-07-editor-draft-head-locks.md)
- [ST-14-08: Editor sandbox settings isolation](../stories/story-14-08-editor-sandbox-settings-isolation.md)

## Out of scope

- Admin quick-create + slug lifecycle stories (ST-14-01, ST-14-02).
- AI/editor intelligence features; ST-08-17 moved to `SPR-2026-05-12`.
- New curated tool authoring flows beyond sandbox iteration.
- Post-publish slug edits, aliases, or redirects.

## Decisions required (ADRs)

- ADR-0038: Editor sandbox interactive actions (accepted)
- ADR-0044: Editor sandbox preview snapshots (accepted)
- ADR-0045: Sandbox-only settings contexts (accepted)
- ADR-0046: Draft head locks for editor concurrency (accepted)

## Risks / edge cases

- Lock heartbeat failures causing unexpected read-only states; ensure clear UI and override flow.
- Snapshot TTL expiry interrupting multi-step flows; UI must surface actionable rerun guidance.
- Snapshot payload size limits blocking preview runs; validation errors must be explicit.
- Sandbox settings context hashing must stay <=64 chars and collision-resistant.

## Execution plan

1) Backend storage + migrations (sandbox_snapshots, draft_locks, tool_runs snapshot_id).
2) Handlers + endpoints: preview run, start-action with snapshot_id, sandbox settings resolve/save, draft lock acquire/refresh/force.
3) Frontend: snapshot payload wiring, ToolInputForm + ToolRunActions parity, settings panel, lock UX/read-only mode.
4) Regenerate OpenAPI/TS types and update editor API client usage.
5) Tests + manual verification (lock conflicts, snapshot expiry, settings isolation, next_actions).

## Demo checklist

- Run sandbox with unsaved code/schema and confirm outputs reflect edits.
- Execute a next_action using snapshot_id and show stable multi-step behavior.
- Save sandbox-only settings and confirm they apply to preview runs only.
- Open two editor sessions to verify lock enforcement + force takeover behavior.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.

## Implementation Tracker (checkboxes)

Legend: [x] done · [ ] not done · (BLOCKED) depends on another story/step

Last updated: 2025-12-29

### ST-14-03 — Editor sandbox next_actions parity

- [x] Render next_actions via ToolRunActions.
- [x] Submit next_action executes same tool version in sandbox context; returns run_id.
- [x] Persist normalized_state to tool_sessions under sandbox context; next action uses server-owned state.
- [x] Stale expected_state_rev returns 409; UI shows actionable conflict.
- [x] html_to_pdf_preview demo tool E2E in sandbox.

### ST-14-04 — Sandbox input_schema form preview parity

- [x] Non-file fields render via ToolInputForm.
- [x] No input_schema → show multi-file picker (upload-first parity).
- [x] input_schema includes file field → show picker with label/accept/min/max parity.
- [x] input_schema exists with no file field → hide picker.
- [x] Invalid input_schema JSON → actionable parse error; no crash.
- [x] Invalid non-file input values → block run; field-level errors; runner not invoked.
- [x] Unsaved valid schema used for preview.

### ST-14-05 — Editor sandbox settings parity

- [x] settings_schema → settings toggle + ToolRunSettingsPanel in sandbox.
- [x] Save settings → next sandbox run receives values via SKRIPTOTEKET_MEMORY_PATH.
- [x] No settings_schema → hide settings UI.
- [x] Invalid schema JSON → parse error and disable settings save.
- [x] Unsaved valid settings_schema used for sandbox settings validation/save.

### ST-14-06 — Editor sandbox preview snapshots

- [x] Unsaved code/schemas run uses snapshot payload (not last saved draft).
- [x] start_action requires snapshot_id and executes against same snapshot.
- [x] Snapshot expires → actionable error prompting rerun.
- [x] Session/files isolated per snapshot_id (sandbox:{snapshot_id}).
- [x] Run details include snapshot_id for continuation after reload.
- [x] Snapshot payload size limits enforced with clear validation errors.
- [x] Lock enforcement for preview run + start-action.

### ST-14-07 — Editor draft head locks

- [x] Acquire lock on editor load + refresh via heartbeat.
- [x] Second user → read-only for draft edits + sandbox; metadata still editable.
- [x] Force takeover (admin/superuser) and previous holder loses permissions.
- [x] Expired lock can be acquired without manual intervention.
- [x] Backend enforces lock ownership for saves + sandbox operations.
- [x] Lock updates to new draft head in same transaction when save advances head.

### ST-14-08 — Editor sandbox settings isolation

- [x] Sandbox settings stored per user + draft head; do not affect production settings.
- [x] Unsaved valid schema used for resolve/save and validation.
- [x] Invalid schema JSON → parse error and disables saving.
- [x] Saved settings applied to next sandbox preview run via SKRIPTOTEKET_MEMORY_PATH.
- [x] No settings_schema → settings panel hidden.
- [x] User without draft lock → API rejects resolve/save.

## Wrap-up

### Scope delivered

- Snapshot-based sandbox preview runs with stable next_actions and session context.
- Draft head locks enforced in API + SPA (heartbeat + takeover + read-only gating).
- Sandbox input and settings parity with production run UI.
- Sandbox settings isolation via sandbox-only settings context.

### Verification (selected)

- Backend: `pdm run lint`, `pdm run typecheck`, `pdm run test`.
- Frontend: `pdm run fe-gen-api-types`, `pdm run fe-type-check`, `pdm run fe-lint`.
- UI smoke: `pdm run ui-editor-smoke` (Playwright; escalation on macOS).
- Manual E2E:
  - `pdm run python -m scripts.playwright_st_14_05_editor_sandbox_settings_e2e`
  - `pdm run python -m scripts.playwright_st_14_03_editor_sandbox_html_to_pdf_preview_e2e`

### Ops notes

- Sandbox snapshot TTL cleanup must be scheduled server-side via systemd timer.
- See `docs/runbooks/runbook-home-server.md` and `docs/runbooks/runbook-observability.md`.

## Notes / follow-ups

- This sprint is adjacent to future editor intelligence and AI assistance work, but
  deliberately focuses on editor workflow correctness and draft safety rather than
  AI-driven authoring features.
- Sandbox settings decisions locked (ST-14-05/08): POST resolve + PUT save endpoints,
  settings service wrapper around tool_sessions, ExecuteToolVersion settings_context
  override, and a new useSandboxSettings.ts composable that reuses helpers from
  useToolSettings.ts.
