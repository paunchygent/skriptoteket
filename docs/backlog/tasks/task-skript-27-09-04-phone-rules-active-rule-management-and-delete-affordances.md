---
type: task
id: TASK-SKRIPT-27-09-04
title: Phone rules active-rule management and delete affordances
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-27-09
task_kind: story
acceptance_criteria:
- Given persisted smart rules exist, when the teacher opens `Regler` on a phone-sized
  viewport, then an `Aktiva regler` management surface is reachable without switching
  to the desktop inspector.
- Given `Nära läraren` preferences exist, when the phone active-rules surface renders,
  then they appear as one consolidated rule row with edit and delete affordances that
  call the existing near-teacher edit and clear actions.
- Given persisted `Håll nära` or `Håll isär` relationship rules exist, when the phone
  active-rules surface renders, then each persisted rule row has edit and delete affordances
  that call the existing relationship-rule edit/delete actions by rule id.
- Given active-template `Fast plats` rules exist, when the phone active-rules surface
  renders, then each persisted fixed-seat rule row has edit and delete affordances
  that call the existing fixed-seat edit/delete actions by rule id.
- Given fixed-seat rules exist for another classroom template, when the phone active-rules
  surface renders, then those rules are not shown or deleted from the active-template
  phone management surface.
- Given the phone active-rules surface is rendered, when no persisted rule exists,
  then it does not add a bulky empty management panel to the reduced rules workflow.
- Given the desktop rules workspace renders, when this slice ships, then the existing
  `PlannerRulesInspector` edit/delete behavior remains unchanged.
- Given a delete action is triggered from phone, when the shared smart-rule lane autosaves,
  then the same roster-owned smart-rule persistence contract is used as desktop; no
  backend endpoint or phone-only storage model is introduced.
- Given a persisted relationship rule is edited after authenticated workspace rehydration,
  when selected candidates are cleared or removed on either desktop or phone, then
  the transient edit panel stays cleared until the user explicitly edits the persisted
  rule again.
- Given persisted `Nära läraren` preferences exist, when the teacher opens or reloads
  `Regler` on phone or desktop, then the persisted rule is visible but its students
  are not copied into `Valda elever` / pending chips until the teacher explicitly
  clicks edit.
- Given draft or roster smart-rule autosave already has a request in flight, when
  a second mutation is queued and a transition flush runs, then the flush waits for
  the queued save before reporting `saved`.
dependencies:
- TASK-SKRIPT-REP-0024
---

## Context
### Problem
`ST-29-17` made the small-screen `Regler` workspace compact and tool-first, but
it left a management gap: phone users can create rules and select pending
students, but they do not have the desktop inspector's visible way to remove
persisted rules.

The underlying model already supports deletion:

- `Nära läraren` is stored as roster-owned `seating_preferences[]` and desktop
  clears the consolidated rule through `clearNearTeacherRule()`.
- `Håll nära` and `Håll isär` are stored as roster-owned
  `relationship_rules[]` and desktop deletes by `rule.id`.
- `Fast plats` is stored as roster-owned `fixed_seat_rules[]`, scoped by
  `template_id`, and desktop deletes active-template rules by `rule.id`.

The phone gap is presentation and event routing, not persistence.

During implementation, live authenticated testing exposed two shared
desktop/phone defects in the same rules state boundary:

- Persisted `Nära läraren` preferences were incorrectly copied into transient
  candidate selection on `Regler` entry/reload. Container logs showed only the
  normal workspace/smart-rules reload requests, and database inspection showed
  the affected roster held saved `near_teacher` preferences, not a persisted
  "selected candidates" model. The frontend root cause was that workspace
  entry activated `beginNearTeacherEdit()`, the explicit edit hydrator, instead
  of activating a blank `near_teacher` tool.
- A separate autosave-lane edge could report a transition flush as saved after
  the first in-flight request while a queued follow-up save still had to run.
  That made authenticated reload proof vulnerable to stale smart-rule truth.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Story Contract Slice
### Goal
Add a compact phone-only `Aktiva regler` surface that mirrors the desktop
inspector's persisted-rule management without turning the phone rules workspace
into a heavy management page.

The phone surface should:

- stay below rule-type choice and above pending selection
- show a count and compact persisted-rule rows
- expose edit and delete icon affordances for each persisted rule family
- route every mutation through the same planner-state actions used by desktop
- preserve the reduced phone hierarchy from `PR-0290`
### Non-goals
- No backend or API contract change.
- No new smart-rule storage model.
- No change to Smart solver diagnostics, scoring, or marker semantics.
- No redesign of the desktop `PlannerRulesInspector`.
- No confirmation dialog for each rule delete in this slice; this follows the
  existing desktop direct-delete behavior.
- No attempt to manage fixed-seat rules from inactive classroom templates on
  phone.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Plan
### Implementation Plan
1. Create a small prop/event-driven `PlannerPhoneRulesSummary.vue` component
   rather than growing `PlannerRulesWorkspacePane.vue`, which is already near
   the file-size boundary.
2. Reuse existing presentation helpers from
   `classroomPlannerSmartRulePresentation.ts` so desktop and phone labels stay
   aligned.
3. Render the phone summary only when at least one persisted active rule exists.
4. For `Nära läraren`, render one consolidated row and emit
   `edit-near-teacher` / `delete-near-teacher`.
5. For relationship rules, render one row per persisted rule and emit
   `edit-rule` / `delete-rule` with the persisted rule id.
6. For fixed-seat rules, consume the parent workspace's active-template filtered
   rule list and emit `edit-fixed-seat-rule` / `delete-fixed-seat-rule` with the
   persisted rule id.
7. Wire the component into the phone branch of `PlannerRulesWorkspacePane.vue`
   using the same handlers already wired to `PlannerRulesInspector.vue`.
8. Add token-owned CSS for dense row layout and touch-safe icon actions.
9. Add component tests that prove phone edit/delete routing for all rule
   families, fixed-seat active-template filtering, empty-state non-rendering,
   and desktop preservation.
10. Add state/action tests where needed to prove deletion still mutates the
    roster-owned smart-rule payload and autosave lane rather than a phone-only
    model.
11. Delete the outdated local HuleEdu Playwright auth helper and route the
    retained PR proof through the current canonical auth-entry helper.
12. Harden both `useRosterSmartRuleLane` and `useDraftPersistenceLane` so
    `flushPendingChanges()` drains queued in-flight saves before reporting
    `saved`.
13. Extend browser proof beyond happy-path phone creation: after authenticated
    save and reload, reselect the persisted roster/classroom, edit the
    rehydrated relationship rule, and prove clear/remove stays cleared on both
    phone and desktop.
14. Keep default rules workspace entry separate from persisted-rule edit:
    default `Nära läraren` activation uses blank authoring state, while the
    active-rule edit affordances remain the only path that hydrates saved rule
    students into `Valda elever` / pending chips.
### Test Plan
- `pdm run fe-test -- --run PlannerPhoneRulesSummary PlannerRulesWorkspacePane useClassroomState classroomPlannerSmartRuleActions`
- `pdm run fe-test -- --run useRosterSmartRuleLane useDraftPersistenceLane useSmartRuleUiState useClassroomState PlannerRulesMapCanvas PlannerRulesWorkspacePane PlannerWorkspaceShell ClassroomPlannerGuestWorkspaceShell PlannerPhoneRulesSummary`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py tests/unit/web/test_pr_0253_auth_retirement_contracts.py -q`
- `pdm run ruff check scripts/playwright_pr_0315_phone_rules_active_management.py tests/unit/web/test_pr_0253_auth_retirement_contracts.py`
- `pdm run python -m scripts.playwright_pr_0315_phone_rules_active_management --base-url http://127.0.0.1:5173`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
### Rollback Plan
Remove `PlannerPhoneRulesSummary.vue`, its phone-workspace insertion, and its
phone CSS. The desktop inspector and existing smart-rule action methods remain
untouched.

## Implementation Steps
The source record did not define a separate section for this package heading.

## Proof
The source record did not define a separate section for this package heading.

## Validation
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Lessons Learned
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Implementation Review
The source record did not define a separate section for this package heading.
