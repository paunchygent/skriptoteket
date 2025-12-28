---
type: story
id: ST-14-05
title: "Editor sandbox settings parity (draft-first)"
status: ready
owners: "agents"
created: 2025-12-27
epic: "EPIC-14"
acceptance_criteria:
  - "Given a draft tool version defines settings_schema, when the editor sandbox is shown, then a Settings toggle appears and renders fields using ToolRunSettingsPanel (same component as ToolRunView)."
  - "Given a user saves settings in the editor sandbox, when the next sandbox run starts, then the runner receives those values via SKRIPTOTEKET_MEMORY_PATH and the tool output reflects the saved settings."
  - "Given a draft version has no settings_schema, when the editor sandbox is shown, then the settings toggle/panel is hidden."
  - "Given the editor settings schema JSON is invalid, when the sandbox section is displayed, then the UI shows an actionable parse error and disables settings save."
  - "Given the editor has unsaved settings_schema text that is valid, when saving sandbox settings, then the values are validated against the unsaved schema and saved for the sandbox preview."
dependencies:
  - "ADR-0022" # UI action field schema contract
  - "ADR-0024" # tool_sessions + state_rev
  - "ADR-0027" # SPA-only UI surface
  - "ADR-0030" # OpenAPI TS types
  - "ADR-0045" # sandbox settings isolation
  - "ST-12-03" # Personalized tool settings
  - "ST-14-06" # Snapshot preview runs
  - "ST-14-08" # Sandbox settings isolation
ui_impact: "Yes (SandboxRunner settings panel + toggle)"
data_impact: "Yes (editor settings endpoints, tool_sessions writes)"
risks:
  - "Invalid schema edits can block settings save; UI must show actionable messages."
---

## Context

Tool authors can define `settings_schema` on draft tool versions, but the editor sandbox does not provide any UI to
edit or persist settings values. This blocks validation of tools that read `SKRIPTOTEKET_MEMORY_PATH` without
publishing a version first.

## Goal

Add editor-sandbox parity for settings:

- Render settings fields in the sandbox using the same UI as `ToolRunView`.
- Persist values per user and apply them to sandbox runs.

## Non-goals

- Changing the settings schema format or supported field kinds (ST-12-03).
- Editor sandbox preview execution behavior is defined in ST-14-06.

## Decision

Sandbox settings are stored in sandbox-only contexts per ADR-0045 and ST-14-08.
This story focuses on UI parity and editor integration; storage semantics are
defined in the sandbox settings isolation story.

## Implementation plan

### Backend (sandbox settings)

Use the sandbox settings resolve/save endpoints from ST-14-08, which accept
`settings_schema` in the request and store values in sandbox-only contexts.

### Frontend (SandboxRunner UI)

1) Parse and surface settings schema

- In `EditorWorkspacePanel.vue`, parse `settingsSchemaText` into `parsedSettingsSchema` (JSON array).
- Show an inline parse error when invalid (parity with input_schema).
- Pass `parsedSettingsSchema` and `settingsSchemaError` into `SandboxRunner.vue`.

2) Render settings panel

- In `SandboxRunner.vue`, reuse `ToolRunSettingsPanel.vue`.
- Add a settings toggle button similar to `ToolRunView`.
- Use a new composable (or extracted helpers from `useToolSettings.ts`) to:
  - fetch settings via the editor endpoints
  - map form values to API values
  - save with `expected_state_rev`
- Allow settings save for valid schemas, even when other editor fields are unsaved.

3) Apply settings to sandbox preview runs

- Sandbox preview runs read the sandbox settings via `SKRIPTOTEKET_MEMORY_PATH`.

### Tests / verification

- Playwright (required patterns in `scripts/`):
  - Seed `demo-settings-test` (script bank).
  - Open editor sandbox, set `theme_color`, save settings, run sandbox.
  - Assert output includes `theme_color=<value>` and persists on reload.
- Manual: open editor sandbox for a draft with settings_schema and confirm the toggle/panel + save flow.
- Live functional check (REQUIRED): run backend + SPA dev, verify in browser, and record steps in `.agent/handoff.md`.
