---
type: story
id: ST-12-07
title: "Explicit session file reuse/clear controls for initial runs"
status: ready
owners: "agents"
created: 2025-12-26
epic: "EPIC-12"
acceptance_criteria:
  - "Given a tool has a prior session with persisted files, when the user starts a new initial run without uploads and opts in to reusing previous files, then the previous session files are injected into /work/input/ for the initial run."
  - "Given a tool has a prior session with persisted files, when the user selects 'clear session files' and starts a new initial run, then no session files are injected and the persisted session files are deleted."
  - "Given a tool is form-only (no uploads provided), when the user starts an initial run without opting in to reuse, then the tool runs with an empty /work/input/ and no implicit session-file reuse occurs."
  - "Given a sandbox run for a tool version, when the user opts in/out of reuse, then the same semantics apply in sandbox context (context = sandbox:{version_id})."
dependencies: ["ST-12-05", "ADR-0039", "ADR-0038"]
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

## UI changes (SPA)

- Checkbox on the run form: “Återanvänd tidigare filer” (maps to `session_files_mode="reuse"`)
- Button: “Rensa sparade filer” (maps to `session_files_mode="clear"`)
- Optional: show the currently persisted session file names for the session context to make reuse explicit.

## Test plan

- Unit: request parsing defaults (`none`), plus the explicit `"reuse"` and `"clear"` semantics.
- Integration: verify `/work/input/` contains persisted files on initial runs when `session_files_mode="reuse"`.
- E2E: a tool that supports “default asset unless overridden” (e.g. CSS) shows deterministic behavior with reuse.
