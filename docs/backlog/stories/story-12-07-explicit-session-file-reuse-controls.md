---
type: story
id: ST-12-07
title: "Explicit session file reuse/clear controls for initial runs"
status: done
owners: "agents"
created: 2025-12-26
epic: "EPIC-12"
acceptance_criteria:
  - "Given a tool has a prior session with persisted files, when the user starts a new initial run without uploads and opts in to reusing previous files, then the previous session files are injected into /work/input/ for the initial run."
  - "Given a tool has a prior session with persisted files, when the user selects 'clear session files' and starts a new initial run, then no session files are injected and the persisted session files are deleted."
  - "Given a tool is form-only (no uploads provided), when the user starts an initial run without opting in to reuse, then the tool runs with an empty /work/input/ and no implicit session-file reuse occurs."
  - "Given a sandbox run for a tool version, when the user opts in/out of reuse, then the same semantics apply in sandbox context (context = sandbox:{snapshot_id})."
dependencies: ["ST-12-05", "ADR-0039", "ADR-0038", "ADR-0044"]
ui_impact: "Yes"
data_impact: "No"
---

## Context

ST-12-05 adds session-scoped file persistence for action runs. To avoid surprising behavior, the MVP does not
implicitly inject prior session files into *initial* runs when no uploads are provided.

Some workflows benefit from explicit reuse of prior files across initial runs (e.g. rerun with different inputs
without reupload, or “use default CSS unless overridden”). This story introduces an explicit, user-controlled
mechanism for reuse/clear so semantics are unambiguous and visible.

## Proposed API surface (minimal)

Add optional form fields to initial run endpoints (defaults preserve current behavior):

- `session_context: str` (default: `"default"`)
- `session_files_mode: "none" | "reuse" | "clear"` (default: `"none"`)

Precedence:

- If uploads are provided: store/replace session files from uploads (ST-12-05); `session_files_mode` is ignored.
- If no uploads are provided:
  - `"none"`: do not inject session files into `/work/input/`
  - `"reuse"`: inject persisted session files into `/work/input/` for this run
  - `"clear"`: clear persisted session files before running; run with empty `/work/input/`

Endpoints:

- Production: `POST /api/v1/tools/{slug}/run`
- Sandbox: `POST /api/v1/editor/tool-versions/{version_id}/run-sandbox`

Sandbox runs should use `session_context = sandbox:{snapshot_id}` per ADR-0044 (not `{version_id}`), so reuse/clear
scopes to the snapshot session.

## Implementation plan (draft)

1) Commands + handlers

   - Extend `RunActiveToolCommand` and `RunSandboxCommand` with `session_context` and `session_files_mode` (defaults: `"default"` + `"none"`).
   - If uploads are present, keep the current behavior (store/replace files).
   - If no uploads, apply `session_files_mode`: `"none"` (no injection), `"reuse"` (inject persisted files), `"clear"` (clear session files, then run empty).
   - For sandbox runs, derive `session_context` as `sandbox:{snapshot_id}` from the run response.

2) Web/API parsing

   - Accept optional form fields on both endpoints; validate allowed modes and map to commands.
   - Keep defaults so existing clients remain unchanged.

3) SPA UI

   - Add “Återanvänd tidigare filer” and “Rensa sparade filer” controls to the run form.
   - Send `session_files_mode` in FormData; only send `session_context` if needed in the UI.

4) Tests

   - Unit tests for handler behavior with protocol mocks (reuse/clear/none).
   - API tests for request parsing defaults + explicit values.
   - SPA unit tests (Vitest) for form submission; optional Playwright for end-to-end reuse/clear flow.

## UI changes (SPA)

- Checkbox on the run form: “Återanvänd tidigare filer” (maps to `session_files_mode="reuse"`)
- Button: “Rensa sparade filer” (maps to `session_files_mode="clear"`)
- Optional: show the currently persisted session file names for the session context to make reuse explicit.

## Test plan

- Unit: request parsing defaults (`none`), plus the explicit `"reuse"` and `"clear"` semantics.
- Integration: verify `/work/input/` contains persisted files on initial runs when `session_files_mode="reuse"`.
- E2E: a tool that supports “default asset unless overridden” (e.g. CSS) shows deterministic behavior with reuse.

## Implementation (done)

- Backend reuse/clear semantics for initial runs (production + sandbox): `src/skriptoteket/application/scripting/handlers/run_active_tool.py`,
  `src/skriptoteket/application/scripting/handlers/run_sandbox.py`, `src/skriptoteket/application/scripting/commands.py`.
- Session file listing APIs + handlers: `src/skriptoteket/application/scripting/handlers/list_session_files.py`,
  `src/skriptoteket/application/scripting/handlers/list_sandbox_session_files.py`,
  `src/skriptoteket/web/routes/interactive_tools.py`,
  `src/skriptoteket/web/api/v1/editor/sandbox.py`.
- SPA UI + API wiring: `frontend/apps/skriptoteket/src/components/tool-run/SessionFilesPanel.vue`,
  `frontend/apps/skriptoteket/src/views/ToolRunView.vue`,
  `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`,
  `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts`.
- Tests: `tests/unit/application/scripting/handlers/test_run_active_tool_session_files.py`,
  `tests/unit/application/scripting/handlers/test_run_sandbox_session_files.py`,
  `tests/unit/web/test_tools_api_routes.py`,
  `tests/unit/web/test_editor_sandbox_api.py`,
  `frontend/apps/skriptoteket/src/components/tool-run/SessionFilesPanel.spec.ts`.
