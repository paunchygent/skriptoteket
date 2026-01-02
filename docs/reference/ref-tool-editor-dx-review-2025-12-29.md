---
type: reference
id: REF-tool-editor-dx-review-2025-12-29
title: "Tool editor DX review (source, schemas, runner, sandbox)"
status: active
owners: "agents"
created: 2025-12-29
topic: "Tool editor DX review and improvement backlog"
---

## Purpose

This document captures a source-based review of the current **tool editor** experience in Skriptoteket (SPA),
covering:

- Tool authoring UX/DX (editor + workflow + sandbox preview)
- JSON setup (`settings_schema`, `input_schema`) and their semantics
- Execution infrastructure (runner, artifacts, snapshots, sessions)
- Key improvement opportunities and a proposed sequence of follow-up sprints

## Current implementation map

### Frontend (SPA)

- Main editor route surface: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
- Workspace panel (code + schemas + sandbox runner + drawers): `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- Code editor (Python): `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`
- Editor sandbox runner (snapshot payload + next_actions parity): `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`
- Draft locking: `frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`
- Tool schema parsing (frontend): `frontend/apps/skriptoteket/src/composables/editor/useEditorSchemaParsing.ts`
- Tool run inputs handling (runtime + sandbox): `frontend/apps/skriptoteket/src/composables/tools/useToolInputs.ts`
- Editor intelligence (lint/completions/hover): `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`

### Backend (API + app services)

- Editor boot (tool/version selection + save mode): `src/skriptoteket/web/api/v1/editor/boot.py`
- Draft saves + create draft: `src/skriptoteket/web/api/v1/editor/drafts.py`
- Draft locks (acquire/release): `src/skriptoteket/web/api/v1/editor/locks.py`
- Sandbox preview runs + start-action: `src/skriptoteket/web/api/v1/editor/sandbox.py`
- Sandbox settings resolve/save: `src/skriptoteket/web/api/v1/editor/sandbox_settings.py`
- Run details + artifact download (editor): `src/skriptoteket/web/api/v1/editor/runs.py`
- Execution pipeline (normalize inputs/settings, compile check, run, normalize ui_payload): `src/skriptoteket/application/scripting/handlers/execute_tool_version_pipeline.py`
- UI payload normalization + budgets: `src/skriptoteket/domain/scripting/ui/normalizer/_deterministic.py`

### Runner + storage

- Docker runner isolation + env injection: `src/skriptoteket/infrastructure/runner/docker_runner.py`
- Runner entrypoint contract v2 coercion: `runner/_runner.py`
- Artifact safety + extraction: `src/skriptoteket/infrastructure/runner/path_safety.py`
- Sandbox snapshots table: `src/skriptoteket/infrastructure/db/models/sandbox_snapshot.py`
- Session state storage (tool_sessions): `src/skriptoteket/infrastructure/repositories/tool_session_repository.py`
- Session file persistence (sandbox/action flows): `src/skriptoteket/infrastructure/session_files/local_session_file_storage.py`

## Strengths

- End-to-end sandbox iteration is strong: snapshots + lock enforcement + next_actions parity + sandbox-only settings.
- The runner is reasonably well isolated (no network, non-root user, caps dropped, read-only FS, tmpfs).
- Deterministic UI payload normalization + budgets keep the UI contract safe and bounded.
- Editor intelligence already provides meaningful “guardrails” for common mistakes.

## Key friction / risks

### 1) `input_schema` semantics are easy to get wrong

Current runtime logic treats:

- `input_schema == null` as “legacy upload-first” (files required to run)
- `input_schema == []` as “schema exists but no fields” (can run without files)

In the editor, an empty textarea becomes `null`, which silently maps to “files required”.

**Update (2026-01-02)**: We plan to remove `input_schema == null` entirely (prototype stage; no user-generated tools in
production yet). “Files required/optional” will be represented as schema via a `file` field (`min/max`), so the editor
and runtime have one schema-driven input model.

### 2) Schema authoring UX is the weakest part of the editor

`settings_schema` and `input_schema` are raw textareas with minimal validation (JSON array only), so author feedback is
late (on save/run) and often not contextual.

### 3) Sandbox debugging is likely too opaque

The runner intentionally surfaces safe `error_summary`, while tracebacks go to stderr. The SPA editor does not expose
stdout/stderr, so authors can’t self-debug most Python errors without server-side logs.

### 4) Review workflow lacks “compare what changed”

Version history navigation exists, but reviewers lack a first-class diff/compare view across:

- source_code
- entrypoint
- schemas
- usage instructions

## Proposed follow-up sprints (skeleton backlog)

All sprint skeletons below are drafted as ~2-work-day “vertical slice” increments.

- Sprint 2026-03-03: Tool editor DX quick wins — `docs/backlog/sprints/sprint-2026-03-03-tool-editor-dx-quick-wins.md`
- Sprint 2026-03-17: Sandbox debug details — `docs/backlog/sprints/sprint-2026-03-17-tool-editor-sandbox-debug-details.md`
- Sprint 2026-03-31: Schema editor v1 — `docs/backlog/sprints/sprint-2026-03-31-tool-editor-schema-editor-v1.md`
- Sprint 2026-04-14: Schema validation v1 — `docs/backlog/sprints/sprint-2026-04-14-tool-editor-schema-validation-v1.md`
- Sprint 2026-04-28: Version diff v1 — `docs/backlog/sprints/sprint-2026-04-28-tool-editor-version-diff-v1.md`
- Sprint 2026-05-12: Runner toolkit + editor intelligence — `docs/backlog/sprints/sprint-2026-05-12-tool-editor-runner-toolkit-and-intelligence.md`
- Sprint 2026-05-26: Tool interaction DX high-yield wins — `docs/backlog/sprints/sprint-2026-05-26-tool-interaction-dx-high-yield.md`
- Sprint 2026-06-09: Tool UI contract v2.x (action defaults + file references) — `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`
- Sprint 2026-06-23: Tool layout editor v1 (contract + renderer) — `docs/backlog/sprints/sprint-2026-06-23-tool-layout-editor-v1-contract-and-renderer.md`
- Sprint 2026-07-07: Tool layout editor v1 (drag/drop) — `docs/backlog/sprints/sprint-2026-07-07-tool-layout-editor-v1-drag-and-drop.md`

Related ADR:

- `docs/adr/adr-0047-layout-editor-v1.md`

## Pro mode: combined bundle view (proposal)

Some authors prefer a “single artifact” editing experience. A proposed Pro mode is a combined editor buffer that
contains `tool.py`, `input_schema.json`, and `settings_schema.json` as delimited sections, while persistence remains
separate fields.

See: `docs/backlog/stories/story-14-29-editor-pro-mode-combined-bundle-view.md`

## Interactive “gap” triage (authoring + runtime)

The items below come up frequently when authoring or using multi-step interactive tools.

### High value, mostly solvable via DX/conventions (no UI contract change)

- **Collect-only step semantic**: model as a regular run that only emits outputs/validation + sets `state` for next step.
- **State handoff clarity**: address via runner toolkit helpers (read/write `action.json` + `state`) and docs.
- **File reference in actions**: address via input manifest + documented conventions (store selected file name(s) in
  `state`, resolve to `/work/input/...` in the runner using a helper).
- **Progress indication**: address via a documented `state.progress` convention and a small UI renderer (opt-in).
- **Conditional actions**: already possible per run (tools can return different `next_actions` based on current state),
  but not reactive inside a single form before submit.

### High value, likely requires platform/contract change for a “real” fix

- **Prefilled action fields**: true prefill/defaults sourced from state/prior input need contract support; a high-yield
  partial workaround is client-side “sticky inputs” (remember last submitted values).

See: `docs/backlog/sprints/sprint-2026-05-26-tool-interaction-dx-high-yield.md`

See also: `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`

## North-star use case: Seating planner (multi-step, interactive layout)

Concrete scenario we want the platform to support well:

1) User provides a roster list (paste or upload).
2) Tool parses and extracts students.
3) User configures a simple “slot” interface:
   - desks/tables as rectangles with a student slot
   - desks can be grouped into rows (1–5 per row) inside a “room” rectangle
   - room orientation objects (door, window, whiteboard)
4) Tool generates an initial placement constrained to slots + additional logic (gender, student attributes, previous
   placement, settings).
5) User manually moves students between slots to fine-tune.
6) User finalizes → tool outputs:
   - an artifact (downloadable)
   - a JSON representation of layout + groups + student names + assignments
7) User returns later → prior rosters/layouts are available from memory and can be used as a starting point.
8) Repeat with tweaks/filters and remembered preferences.

How this maps to the planned work:

- **Now (possible but clunky)**: steps 1–2, 4, 6–8 are straightforward with current `input_schema`, `next_actions`, `state`,
  artifacts, and settings; step 5 can be modeled with action forms (swap/move) but lacks the slot UI.
- **High-yield UX**: sticky action inputs + progress + file reference UX (SPR-2026-05-26) make multi-step iteration
  tolerable even before deeper contract work.
- **Contract v2.x**: action defaults/prefill + file references (SPR-2026-06-09) enable “real” guided flows and clean
  reuse of previous rosters/layouts.
- **Layout editor v1**: a first-class interactive “layout editor” output type (platform-rendered, no arbitrary tool JS)
  unlocks the intended slot editor experience:
  - contract + click-to-assign (SPR-2026-06-23)
  - drag/drop enhancement (SPR-2026-07-07)
  - ADR foundation: `docs/adr/adr-0047-layout-editor-v1.md`

## Deferred “bigger bets” (not included in the sprint skeleton set)

- Schema “v2” (defaults/required/help/min/max/placeholder) across domain + OpenAPI + SPA.
- Vega-Lite end-to-end support (policy + normalization + client renderer).
- Runner scaling hardening (shared capacity limiter across replicas + orphan cleanup).
