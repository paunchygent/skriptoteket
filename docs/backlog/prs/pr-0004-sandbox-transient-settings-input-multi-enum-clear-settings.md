---
type: pr
id: PR-0004
title: "Sandbox transient settings + input multi_enum + clear settings API"
status: ready
owners: "agents"
created: 2026-01-05
updated: 2026-01-05
stories:
  - "ST-14-05"
  - "ST-14-08"
  - "ST-12-03"
  - "ST-12-04"
tags: ["backend", "frontend", "ux"]
acceptance_criteria:
  - "Given the editor sandbox settings form has unsaved values, when testkor starts, then the run uses those transient settings values without persisting them."
  - "Given a published tool has saved settings, when the user clears settings, then persisted settings are removed and subsequent runs use defaults."
  - "Given sandbox settings are saved, when the user clears sandbox settings, then the sandbox settings store is reset without affecting production settings."
  - "Given input_schema uses multi_enum, when the user runs a tool, then the UI renders the input and the runner receives the selected values via SKRIPTOTEKET_INPUTS."
---

## Problem

Sandbox test runs do not use the currently selected settings unless they are
explicitly saved, which violates parity with the editor workflow. Additionally,
there is no explicit way to clear persisted settings, neither in the editor nor
for published tools in /tools, and input_schema lacks multi_enum parity with settings.

## Goal

- Allow sandbox runs to use transient (unsaved) settings values without
  persisting them.
- Add a clear settings API for both production and sandbox settings.
- Add input_schema multi_enum support to align input and settings capabilities.

## Non-goals

- Introducing non-persisted settings in production (settings remain persisted).
- Changing settings schema contract or field kinds outside multi_enum parity.

## Implementation plan

1) Sandbox transient settings
   - Extend sandbox run API to accept `settings_values` (JSON object).
   - Validate against the snapshot settings schema and use for that run only.
   - Do not persist; saved sandbox settings remain separate.

2) Clear settings API
   - Add DELETE endpoints:
     - `/api/v1/tools/{tool_id}/settings`
     - `/api/v1/editor/tool-versions/{version_id}/sandbox-settings`
   - Implement handlers to delete/reset session state for the settings context.

3) Input schema multi_enum
   - Add `multi_enum` to input schema domain model + validation.
   - Update OpenAPI types and frontend input rendering + value normalization.

4) UI wiring
   - Add "Rensa" action to production settings UI and sandbox settings card.
   - Ensure clear operations update local state and show success feedback.
   - Pass transient settings values into sandbox run requests.

## Test plan

- Backend unit tests: transient settings validation, clear settings endpoints,
  multi_enum input normalization.
- Frontend tests: settings clear UX and multi_enum input rendering.
- Manual: sandbox run uses unsaved settings; clear settings resets output.

## Rollback plan

- Remove transient settings from sandbox run and delete clear endpoints.
- Revert input_schema multi_enum support and UI wiring.
