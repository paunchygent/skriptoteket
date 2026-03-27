---
type: story
id: ST-27-06
title: "Klassrumskartan — Planner session lanes and transition matrix remediation"
status: done
owners: "agents"
created: 2026-03-27
epic: "EPIC-27"
dependencies: ["ST-27-01"]
acceptance_criteria:
  - "Given the planner loads or switches workspaces, when a new session begins, then one session controller is the only source of truth for active draft and roster identity while draft and smart-rule lanes keep only bound IDs for request guarding."
  - "Given roster smart-rule hydration fails after the current draft workspace has loaded, when the teacher stays in the planner, then the draft lane remains usable, smart-rule authoring stays disabled, and retry remains available without turning that GET failure into a planner-wide save conflict."
  - "Given the teacher invokes undo or redo while the smart-rule lane is dirty, saving, conflicted, or errored, when the history action runs, then only the draft lane flushes and the smart-rule lane neither PATCHes nor blocks the draft-history action."
  - "Given the teacher abandons the active draft while both lanes have unsaved work, when abandon runs, then pending draft-local edits are discarded explicitly, roster-global smart rules are flushed first, and any continue-anyway choice explicitly says class-wide smart-rule edits will be lost if the smart lane cannot save."
  - "Given the teacher exits the planner while one lane is still pending, when the normal exit wait reaches its timeout, then `exitPlanner` returns an explicit confirm-discard state instead of silently leaving or silently dropping pending work."
  - "Given the teacher chooses `confirmExitWithoutWaiting`, when the planner tears down the session, then both lanes are discarded explicitly and late load/save responses are ignored so cleared planner state cannot repopulate after exit."
  - "Given `clearWorkspace` runs, when the session tears down without route exit, then that transition remains pure teardown with no save network work and late responses cannot repopulate planner state afterward."
  - "Given the teacher leaves the planner screen successfully, when they return to overview or exit the app, then the smart-rule UI bucket resets from explicit transition policy rather than from persistence acknowledgements."
  - "Given draft or smart-rule save acknowledgements arrive, when visible state is reconciled, then those acknowledgements do not reset active smart tools or pending smart-rule selections."
  - "Given this remediation lands, when the frontend module surface is inspected, then `useClassroomState.ts` is reduced to a thin composition layer while dedicated session-controller, draft-lane, smart-rule-lane, smart-rule-UI, and transition-policy modules plus their own specs own the new planner session contract."
  - "Given this remediation lands, when the planner persistence contract is inspected, then no planner-wide `flushPendingSave()`, shared autosave timer, or planner-global persistence truth via `saveStatus` / `saveMessage` remains."
ui_impact: "Yes (planner transition behavior, disablement, and discard messaging)"
data_impact: "No"
---

## Context

`PR-0151` corrected the backend/API ownership boundary to roster-global smart rules and
draft-local arrangement state, but review of the frontend orchestration still found one shared
planner persistence contract underneath the split endpoints. That leftover shape keeps recreating
the same class of issues around workspace switches, history actions, abandon, clear, and route
exit.

## Notes

- This is a docs-approved remediation slice, not a compatibility bridge.
- Do a full cut-over to explicit planner session lanes; do not patch the existing shared save
  contract with more conditional guards.
- The session controller owns active session identity; lanes keep only bound IDs for request
  guarding.
- The draft lane and smart-rule lane each keep their own debounce timer, dirty state, save state,
  and conflict/error handling.
- Smart-rule hydration failure is distinct from smart-rule persistence conflict/error.
- Smart-rule authoring UI state is its own bucket and resets only from explicit transition policy.
- `exitPlanner` timeout, `confirmExitWithoutWaiting`, and `clearWorkspace` teardown semantics are
  part of the locked contract because they are the highest-risk hidden-discard transitions.
- This cut-over must land as dedicated session/lane/UI modules and specs; do not satisfy the story
  by keeping one large `useClassroomState.ts` and adding more conditional branches.
- `ST-27-06` must land before `ST-27-03` and `ST-27-04`; later smart seating/grouping work must
  not build on the current shared planner persistence shape.

## Implementation Summary (as of 2026-03-27)

- `PR-0152` is implemented.
- `useClassroomState.ts` now acts as a thin composition adapter over:
  - `usePlannerSessionController.ts`
  - `useDraftPersistenceLane.ts`
  - `useRosterSmartRuleLane.ts`
  - `useSmartRuleUiState.ts`
  - `plannerTransitionPolicies.ts`
- Route-shell, export, abandon, undo/redo, and exit flows now use explicit transition policies
  instead of planner-wide flush/status/timer behavior.
- `clearWorkspace()` is teardown-only, smart-rule hydration failure stays lane-local with retry UI,
  and exit timeout now returns confirm-discard with explicit discard semantics.
