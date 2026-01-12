---
type: pr
id: PR-0026
title: "Settings suggestions from tool runs"
status: ready
owners: "agents"
created: 2026-01-12
updated: 2026-01-12
stories:
  - "ST-14-34"
tags: ["backend", "frontend", "ux"]
acceptance_criteria:
  - "Tool runs can return settings_suggestions and the UI renders a clean suggestion card (no raw JSON)."
  - "User-confirmed saves validate against settings_schema and persist via existing settings APIs."
  - "Invalid suggestions are rejected with actionable errors and do not persist."
---

## Problem

Tools sometimes compute reusable settings (e.g., class rosters) but today users must copy/paste JSON into settings,
which is a poor UX and error-prone. We need a secure, explicit way for a tool run to propose settings without
allowing the runner to persist settings directly.

## Goal

Implement `settings_suggestions` (ADR-0057) so a tool run can propose settings changes, and the UI can show a
non-JSON suggestion card with a single “Spara” action that uses the existing settings save flow.

## Non-goals

- Allowing the runner to write settings directly.
- Introducing new persistence models for settings (reuse existing per-user tool settings).
- Redesigning the ToolRunView layout beyond the suggestion card.

## Implementation plan

1) Contract + validation
   - Extend `ToolUiContractV2Result` + `UiPayloadV2` with `settings_suggestions`.
   - Define suggestion schema: `key`, `label`, `summary` (optional), `value` (JsonValue).
   - Add normalization/caps (max suggestions, max bytes per suggestion).
2) Backend persistence flow
   - Include `settings_suggestions` in stored `ui_payload`.
   - Expose in run APIs that return ui_payload (ToolRunView + editor sandbox).
3) Frontend UI
   - Add a `ToolRunSettingsSuggestionCard` in ToolRunView + SandboxRunner.
   - Render label + summary, hide raw JSON by default.
   - “Spara” triggers existing `PUT /api/v1/tools/{tool_id}/settings` with
     `values = { [key]: value }` and the current `state_rev`.
   - Show success/failure toasts (reuse existing toast flow).
4) Planned tool GUI story integration
   - Align card styling and placement with the ToolRunView UX conventions
     (see ST-14-22 “Tool run UX conventions for progress + input file references”).
   - Keep cards consistent with other result components in the tool GUI.
5) Follow-up usage
   - Update Gruppgeneratorn to emit a settings_suggestion instead of JSON
     once the platform support exists.

## Test plan

- Unit: contract parsing/validation for `settings_suggestions`.
- Frontend: suggestion card renders; save calls settings API; error toast on invalid payload.
- Manual: run Gruppgeneratorn, click “Spara klasslista”, verify settings persist and apply on next run.

## Rollback plan

- Revert contract extension and UI card; tool runs ignore `settings_suggestions`.
