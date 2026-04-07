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
- Key improvement opportunities and the follow-up backlog themes they imply

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

- `input_schema` as schema-only (never `null`)
- file uploads as an explicit schema `file` field (`min/max`)
- `input_schema == []` as “no inputs” (no pre-run form; no file picker)

**Update (2026-01-02)**: ST-14-09 shipped and removed the legacy `input_schema == null` “upload-first” mode entirely,
so the editor and runtime have one predictable schema-driven input model.

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

## Follow-up backlog themes

- Editor sandbox debug visibility:
  `docs/backlog/stories/story-14-12-editor-sandbox-debug-panel.md`
- Schema editor and validation UX:
  `docs/backlog/stories/story-14-14-editor-schema-editor-snippets-and-diagnostics.md`,
  `docs/backlog/stories/story-14-16-editor-schema-validation-errors-ux.md`
- Version compare/diff:
  `docs/backlog/stories/story-14-17-editor-version-diff-view.md`
- Runner toolkit and editor intelligence:
  `docs/backlog/stories/story-14-19-runner-toolkit-helper-module.md`,
  `docs/backlog/stories/story-14-20-editor-intelligence-toolkit-support.md`
- Tool-run interaction UX, action defaults, and file references:
  `docs/backlog/stories/story-14-22-tool-run-ux-progress-and-file-references.md`,
  `docs/backlog/stories/story-14-23-ui-contract-action-defaults-prefill.md`,
  `docs/backlog/stories/story-14-24-ui-contract-file-references.md`
- Layout editor output and interactions:
  `docs/backlog/stories/story-14-25-ui-contract-layout-editor-v1-output.md`,
  `docs/backlog/stories/story-14-26-ui-renderer-layout-editor-v1-click-assign.md`,
  `docs/backlog/stories/story-14-27-layout-editor-v1-drag-drop.md`,
  `docs/backlog/stories/story-14-28-layout-editor-v1-ux-polish-and-a11y.md`

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
- **State handoff clarity**: address via runner toolkit helpers (read `SKRIPTOTEKET_ACTION` + merge/validate `state`) and docs.
- **File reference in actions**: address via input manifest + documented conventions (store selected file name(s) in
  `state`, resolve to `/work/input/...` in the runner using a helper).
- **Progress indication**: address via a documented `state.progress` convention and a small UI renderer (opt-in).
- **Conditional actions**: already possible per run (tools can return different `next_actions` based on current state),
  but not reactive inside a single form before submit.

### High value, likely requires platform/contract change for a “real” fix

- **Prefilled action fields**: true prefill/defaults sourced from state/prior input need contract support; a high-yield
  partial workaround is client-side “sticky inputs” (remember last submitted values).

See:
`docs/backlog/stories/story-14-22-tool-run-ux-progress-and-file-references.md`

See also:
`docs/backlog/stories/story-14-23-ui-contract-action-defaults-prefill.md` and
`docs/backlog/stories/story-14-24-ui-contract-file-references.md`

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
- **High-yield UX**: sticky action inputs + progress + file reference UX make multi-step iteration
  tolerable even before deeper contract work.
- **Contract v2.x**: action defaults/prefill + file references enable “real” guided flows and clean
  reuse of previous rosters/layouts.
- **Layout editor v1**: a first-class interactive “layout editor” output type (platform-rendered, no arbitrary tool JS)
  unlocks the intended slot editor experience:
  - contract + click-to-assign (`ST-14-25` / `ST-14-26`)
  - drag/drop enhancement (`ST-14-27` / `ST-14-28`)
  - ADR foundation: `docs/adr/adr-0047-layout-editor-v1.md`

## Deferred “bigger bets”

- Schema “v2” (defaults/required/help/min/max/placeholder) across domain + OpenAPI + SPA.
- Vega-Lite end-to-end support (policy + normalization + client renderer).
- Runner scaling hardening (shared capacity limiter across replicas + orphan cleanup).
