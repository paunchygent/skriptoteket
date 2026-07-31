---
type: task
id: TASK-SKRIPT-14-34-01
title: Settings suggestions from tool runs
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-14-34
task_kind: story
acceptance_criteria:
- Tool runs can return settings_suggestions and the UI renders a clean suggestion
  card (no raw JSON).
- User-confirmed saves validate against settings_schema and persist via existing settings
  APIs.
- Invalid suggestions are rejected with actionable errors and do not persist.
---

## Context

### Source: Problem

Tools sometimes compute reusable settings (e.g., class rosters) but today users must copy/paste JSON into settings,
which is a poor UX and error-prone. We need a secure, explicit way for a tool run to propose settings without
allowing the runner to persist settings directly.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

### Source: Goal

Implement `settings_suggestions` (ADR-SKRIPT-0057) so a tool run can propose settings changes, and the UI can show a
non-JSON suggestion card with a single “Spara” action that uses the existing settings save flow.

## Contract Inputs

No separate contract inputs were recorded in the source snapshot.

## Plan

### Source: Implementation plan

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
     (see ST-SKRIPT-14-22 “Tool run UX conventions for progress + input file references”).
   - Keep cards consistent with other result components in the tool GUI.
5) Follow-up usage
   - Update Gruppgeneratorn to emit a settings_suggestion instead of JSON
     once the platform support exists.

## Implementation Steps

The source records no separate implementation steps.

## Proof

### Source: Test plan

- Unit: contract parsing/validation for `settings_suggestions`.
- Frontend: suggestion card renders; save calls settings API; error toast on invalid payload.
- Manual: run Gruppgeneratorn, click “Spara klasslista”, verify settings persist and apply on next run.

## Validation

Validation follows the focused test and verification material recorded above.

## Stop Conditions

### Source: Non-goals

- Allowing the runner to write settings directly.
- Introducing new persistence models for settings (reuse existing per-user tool settings).
- Redesigning the ToolRunView layout beyond the suggestion card.

### Source: Rollback plan

- Revert contract extension and UI card; tool runs ignore `settings_suggestions`.

## Lessons Learned

No separate lessons learned were recorded in the source snapshot.

## Notes

No additional task-local notes were recorded in the source snapshot.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Implementation Review

No separate implementation review was recorded in the source snapshot.
