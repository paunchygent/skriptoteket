---
type: pr
id: PR-0152
title: "Klassrumskartan: planner session lanes and transition matrix remediation"
status: done
owners: "agents"
created: 2026-03-27
updated: 2026-03-27
stories:
  - "ST-27-06"
tags: ["frontend", "state-management", "klassrumskartan", "smart-assignment", "design-remediation"]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0151"
acceptance_criteria:
  - "Given the planner persists draft-local arrangement state and roster-global smart rules, when the frontend save contract is inspected after this slice, then those lanes no longer share one planner-wide flush, timer, or persistence-truth status."
  - "Given a current-roster smart-rule GET fails after a draft workspace loads, when the teacher stays in the planner, then the draft lane remains usable, smart-rule authoring is disabled, and retry is available without treating the failed GET as a whole-session save blocker."
  - "Given the teacher runs undo or redo while the smart-rule lane is dirty, saving, conflicted, or errored, when the history action executes, then only the draft lane flushes and the smart-rule lane neither persists nor blocks that history action."
  - "Given the teacher abandons the active draft while both lanes have unsaved work, when abandon runs, then the smart-rule lane is flushed first, pending draft-local edits are discarded explicitly, and any continue-anyway choice explicitly says class-wide smart-rule edits will be lost if the smart lane cannot save."
  - "Given the teacher exits the planner while one lane is still pending, when the normal exit wait reaches its timeout, then `exitPlanner` returns an explicit confirm-discard state instead of silently leaving or silently discarding pending work."
  - "Given the teacher chooses `confirmExitWithoutWaiting`, when teardown proceeds, then both lanes are discarded explicitly and late load/save responses are ignored so the cleared planner state cannot repopulate after exit."
  - "Given `clearWorkspace` runs outside the normal exit flow, when the planner tears down the current session, then that transition stays pure teardown with no save network work and late responses cannot repopulate planner state afterward."
  - "Given the teacher leaves the planner screen successfully, when they return to overview or exit the app, then smart-rule UI state resets from explicit transition policy rather than from save/load acknowledgements."
  - "Given persistence acknowledgements arrive after draft or smart-rule saves, when visible state is reconciled, then those acknowledgements never reset active smart tools or pending smart-rule selections."
  - "Given this slice lands, when the frontend module surface is inspected, then `useClassroomState.ts` is only a thin composition adapter and dedicated session-controller, draft-lane, smart-rule-lane, smart-rule-UI, and transition-policy modules plus their own specs own the remediation contract."
---

## Problem

`PR-0151` fixed the backend ownership boundary, but the frontend still retains one shared planner
persistence contract under that split. Review of the proposed follow-up design found the remaining
root cause clearly:

- one planner-wide flush concept
- one planner-wide persistence truth via save status/message
- save/load acknowledgement paths that still decide smart-rule UI resets
- hidden discard semantics around abandon and exit

As long as that shape stays in place, the same class of bugs will continue to recur under different
transition names.

## Goal

Replace the shared planner persistence contract with an explicit, ownership-honest frontend model:

- one thin planner session controller
- one draft-local persistence lane
- one roster-global smart-rule persistence/hydration lane
- one separate smart-rule authoring UI bucket
- one explicit transition matrix for `loadWorkspace`, `undo`, `redo`, `abandonDraft`,
  `clearWorkspace`, overview return, and route exit

## Non-goals

- Implementing backend smart seating or smart grouping solver behavior.
- Replacing export-backed checkpoint work in `PR-0150`.
- Adding new teacher-facing smart features beyond clearer disablement/discard semantics.
- Keeping compatibility shims, aliases, or fallback paths for the current shared planner save
  contract.
- Introducing a generic reusable state-machine framework beyond this planner slice.

## Implementation plan

1. Lock the review findings in frontend tests first.
   - Prove smart-rule hydration failure does not become a planner-wide save blocker.
   - Prove smart-rule dirty/conflict/error state neither PATCHes nor blocks undo/redo.
   - Prove abandon explicitly protects or explicitly discards class-wide smart-rule edits.
   - Prove `exitPlanner` timeout returns confirm-discard rather than silently dropping pending
     work.
   - Prove `confirmExitWithoutWaiting` discards both lanes and ignores late responses.
   - Prove `clearWorkspace` remains teardown-only and cannot be followed by late-response
     repopulation.
   - Prove smart-rule UI resets come from transition policy, not save/load acknowledgement paths.

2. Split planner orchestration into explicit contracts.
   - Create a thin session controller as the only source of truth for active session token,
     draft ID, and roster ID.
   - Reduce `useClassroomState.ts` to a composition/adapter surface only.
   - Add dedicated controller/lane/UI modules instead of extending one umbrella store:
     - `usePlannerSessionController.ts`
     - `useDraftPersistenceLane.ts`
     - `useRosterSmartRuleLane.ts`
     - `useSmartRuleUiState.ts`
     - `plannerTransitionPolicies.ts`
   - Split draft persistence into its own lane contract.
   - Split roster smart-rule hydration/persistence into its own lane contract.
   - Keep smart-rule authoring UI state in a separate bucket.

3. Replace the shared planner save contract.
   - Delete planner-wide `flushPendingSave()`.
   - Delete planner-global persistence truth via one save status/message.
   - Use one debounce timer per lane.
   - Keep hydration-failure state distinct from persistence-failure state in the smart-rule lane.

4. Implement the explicit transition matrix.
   - `loadWorkspace`: draft-first, fail-safe, clear old smart rules immediately, disable smart-rule
     authoring until current-roster rules hydrate.
   - `undo` / `redo`: draft-lane-only flush behavior.
   - `abandonDraft`: smart-lane-first persistence, explicit draft discard semantics, explicit
     class-wide smart-rule discard wording for continue-anyway paths.
   - `clearWorkspace`: pure teardown, no save network work, and late-response ignore semantics.
   - `exitPlanner`: explicit timeout-to-confirm-discard behavior.
   - `confirmExitWithoutWaiting`: explicit discard of both lanes plus late-response ignore
     semantics.
   - overview return / route exit: explicit lane policies with no acknowledgement-driven UI resets.

5. Move the route shell onto explicit transition APIs.
   - Replace generic “flush pending save” guard logic with transition-specific lane orchestration.
   - Keep overview return and exit usable when smart-rule hydration failed but no dirty smart-rule
     persistence exists.

## Files expected to change

- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/usePlannerSessionController.ts`
- `frontend/apps/skriptoteket/src/views/apps/usePlannerSessionController.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/useDraftPersistenceLane.ts`
- `frontend/apps/skriptoteket/src/views/apps/useDraftPersistenceLane.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRosterSmartRuleLane.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRosterSmartRuleLane.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/useSmartRuleUiState.ts`
- `frontend/apps/skriptoteket/src/views/apps/useSmartRuleUiState.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/plannerTransitionPolicies.ts`
- `frontend/apps/skriptoteket/src/views/apps/plannerTransitionPolicies.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellSaveGuards.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellExit.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellWorkspace.ts`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`

## PR-sized execution checklist

- [x] Add regressions for smart-rule hydration failure staying lane-local
- [x] Add regressions for smart-rule dirtiness not affecting undo/redo
- [x] Add regressions for explicit abandon discard semantics across both lanes
- [x] Add regressions for exit timeout, confirm-discard, and teardown-only clear semantics
- [x] Split the planner into dedicated session-controller, draft-lane, smart-rule-lane,
  smart-rule-UI, and transition-policy modules
- [x] Reduce `useClassroomState.ts` to a thin composition/adapter surface
- [x] Remove the shared planner-wide flush/save-status contract
- [x] Implement one timer per lane
- [x] Move route-shell transitions onto explicit lane policies
- [x] Add dedicated specs for the new controller/lane/UI modules
- [x] Re-run verification and record it in `.codex/handoff.md`

## Implementation Summary

- `useClassroomState.ts` is now a thin adapter over dedicated session-controller, draft-lane,
  roster smart-rule lane, smart-rule UI, and transition-policy modules.
- Planner-wide `flushPendingSave()`, shared autosave timing, and planner-global persistence truth
  via `saveStatus` / `saveMessage` are removed from the planner contract.
- Route-shell exit/workspace/export flows now call explicit transition APIs, `abandonDraft`
  flushes the smart lane first, and `clearWorkspace()` remains teardown-only with late-response
  ignore semantics.
- Smart-rule hydration failure now stays lane-local with retry UI, while persistence
  acknowledgements no longer reset active smart tools or pending selections.

## Test plan

- `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/usePlannerSessionController.spec.ts src/views/apps/useDraftPersistenceLane.spec.ts src/views/apps/useRosterSmartRuleLane.spec.ts src/views/apps/useSmartRuleUiState.spec.ts src/views/apps/plannerTransitionPolicies.spec.ts`
- `pdm run fe-test -- --run src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- live planner proof on `http://127.0.0.1:5173` with the existing smoke once implementation exists

## Rollback plan

- Revert the frontend lane split together if the explicit session contract proves incorrect.
- Do not fall back to more conditional guards on the current shared planner save machine.
- Preserve the docs trail so later smart seating/grouping work still starts from the corrected
  transition model.
