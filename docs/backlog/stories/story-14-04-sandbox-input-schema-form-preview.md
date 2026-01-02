---
type: story
id: ST-14-04
title: "Editor sandbox input_schema form preview (ToolInputForm parity)"
status: done
owners: "agents"
created: 2025-12-27
updated: 2026-01-02
epic: "EPIC-14"
acceptance_criteria:
  - "Given a draft tool version has input_schema with non-file fields, when the editor sandbox is shown, then the sandbox renders those fields using the same ToolInputForm component as the user ToolRunView."
  - "Given input_schema exists and includes a file field, when the editor sandbox is shown, then the sandbox shows the file picker and uses the schema’s label/accept/min/max behavior (parity with ToolRunView)."
  - "Given input_schema exists and has no file field, when the editor sandbox is shown, then the sandbox hides the file picker (tool does not accept files) (parity with ToolRunView)."
  - "Given input_schema is present but invalid JSON in the editor textarea, when viewing the sandbox section, then the UI shows an actionable parse error and does not crash."
  - "Given non-file input values are invalid (e.g. integer/number coercion, enum not in options), when the user attempts to run the sandbox, then the run is blocked and field-level validation errors are shown (runner is not invoked)."
  - "Given the editor has unsaved input_schema text that is valid, when the user runs the sandbox preview, then the form and validation use the unsaved schema (snapshot preview)."
dependencies:
  - "ADR-0027" # SPA-only UI surface
  - "ADR-0030" # OpenAPI TS types
  - "ST-12-04" # ToolInputForm + useToolInputs coercion/validation rules
  - "ADR-0038" # Sandbox interactivity direction (next_actions/state_rev)
  - "ADR-0039" # Session-scoped file persistence (multi-step + files)
  - "ST-14-06" # Snapshot preview runs
ui_impact: "Yes (SandboxRunner pre-run form + ToolRunView-parity file picker behavior)"
data_impact: "No (frontend-only; uses existing inputs multipart contract)"
---

## Context

Tool authors (admins/contributors) can edit `input_schema` on draft tool versions, but the editor sandbox currently
provides only:

- a raw file picker
- a raw `SKRIPTOTEKET_INPUTS` JSON preview (without any form UI to edit values)

This blocks authors from validating the actual form UX (dropdowns, checkboxes, text inputs) that end users will see in
`ToolRunView`, and forces premature publishing to verify the form renders correctly.

## Goal

Make the editor sandbox render the same pre-run form UI as the user run view, driven by the draft version’s
`input_schema`, so authors can iterate and test before publishing.

## Non-goals

- Change the tool input schema format or extend supported field kinds (ST-12-04 defines v1).
- Reintroduce SSR/legacy UI paths (ADR-0027).
- Make `input_schema` apply to `next_actions` (those use ADR-0022 action schemas and are handled via ToolRunActions).

## Implementation plan (frontend)

### 1) Parse and pass `input_schema` from the editor panel

- In `EditorWorkspacePanel.vue`, parse `inputSchemaText` into `parsedInputSchema`.
- If parsing fails, surface a clear inline error (JSON parse + “must be an array”) and pass `null` (parse error) to the sandbox.
- Pass `parsedInputSchema` into `SandboxRunner.vue`.

### 2) Render ToolInputForm (non-file fields) + schema-driven file picker

In `SandboxRunner.vue`:

- Reuse the existing `ToolInputForm.vue` component to render non-file fields.
- Reuse the same coercion/validation rules as the user run view (ST-12-04) instead of duplicating logic:
  - boolean defaults/handling
  - integer/number parsing
  - enum option validation
  - empty values dropped before API submission
  - file min/max validation + accept UI hint
- Match the published run view logic for showing the file picker:
  - show when `input_schema` includes a file field
  - hide when `input_schema` has no file field (tool does not accept files)

### 3) Allow sandbox preview runs with unsaved schema

Sandbox preview runs use the snapshot payload (ST-14-06), so the run button is only blocked by validation errors,
missing lock ownership, or invalid JSON parse errors.

### 4) Preserve existing sandbox features

- Keep the existing run result polling, UI outputs, artifacts, and multi-step `next_actions` UX (ST-14-03).
- Pre-run inputs apply only to the initial sandbox run; action submissions continue to use ToolRunActions.

## Notes / File touchpoints

- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue` (parse + pass props)
- `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue` (render ToolInputForm + schema-driven file picker)
- Reuse: `frontend/apps/skriptoteket/src/components/tool-run/ToolInputForm.vue`,
  `frontend/apps/skriptoteket/src/composables/tools/useToolInputs.ts`

### Update (2026-01-02)

ST-14-09 removed the legacy `input_schema == null` “upload-first” mode; file uploads are represented only via
`{"kind":"file"}` fields (`min/max`) and “no inputs” is `[]`.

## Test plan

- Live functional check (REQUIRED): run backend + SPA dev and verify in browser; record steps in `.agent/handoff.md`.
- Manual:
  - In the editor, select a draft tool version with `input_schema` containing string/enum/boolean fields and verify the
    form renders and blocks invalid inputs.
  - Verify file min/max enforcement for a tool with a file field.
  - Verify multi-step tool demo (e.g. html→pdf preview) still works: initial run uses inputs + optional files, then
    `next_actions` submission continues to function with session file persistence (ADR-0039).
