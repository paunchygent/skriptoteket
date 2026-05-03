---
type: pr
id: PR-0287
title: "ST-29-11 Smart settings popover persistence"
status: done
owners: "agents"
created: 2026-05-03
updated: 2026-05-03
stories:
  - "ST-29-11"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "toolbar", "smart"]
dependencies:
  - "PR-0281"
  - "PR-0286"
acceptance_criteria:
  - "Given the teacher opens Smart-inställningar from the Smart toolbar split affordance, when they toggle `Historik`, `Smart`, or grouping seating-distance settings inside the panel, then the panel remains open and the setting updates."
  - "Given the Smart settings panel is open, when the teacher clicks the explicit close button, presses Escape, or clicks outside/backdrop, then the panel closes."
  - "Given the teacher chooses `Öppna Regler`, when the workspace navigation starts, then the panel closes as an intentional navigation action."
  - "Given the active workspace identity changes because the teacher switches mode, draft kind, or real template context, then the panel closes; simple draft object replacement with the same identity must not close it."
  - "Given implementation is reviewed, when shell watchers are inspected, then they do not use fresh object/array watcher sources that retrigger close behavior for internal settings edits."
  - "Given proof is run, when authenticated and public/guest shells are exercised, then both grouping and seating Smart settings panels preserve internal interaction state and still close on explicit outside/close paths."
---

## Problem

The Smart settings panel opened from the Smart toolbar affordance currently
closes after internal setting interactions such as the `Historik` toggle. That
does not match teacher expectations for a settings panel: internal controls
should be editable in place, and the panel should stay open until the teacher
closes it or intentionally leaves the context.

The likely implementation cause is in the workspace shell watchers rather than
the toggle itself. Smart setting actions update draft flags by replacing the
draft object. The authenticated and guest shells currently close settings from
watchers that observe fresh array/object values, so an internal draft update can
look like a workspace change.

## Goal

Make the grouping and seating Smart settings panel lifecycle predictable:

- Internal settings changes keep the panel open.
- Explicit close, Escape, outside/backdrop click, and intentional navigation
  close the panel.
- Real workspace identity changes still close the panel.
- Authenticated and guest/public workspace shells share the same behavior.

## Non-goals

- No backend, Smart algorithm, draft persistence, roster smart-rule, or API
  contract changes.
- No change to the meaning of `smart_enabled`, `use_history`, or
  `grouping_seating_distance_enabled`.
- No redesign of the Rules workspace or Smart rule authoring.
- No new global modal/dialog primitive unless the local fix clearly proves a
  repeated cross-surface need.
- No JavaScript-owned toolbar geometry or breakpoint sizing changes.

## Implementation Plan

1. Add focused failing coverage in `PlannerWorkspaceShell.spec.ts` for
   authenticated grouping and seating:
   - open Smart settings
   - interact with internal toggles/selects
   - assert the settings panel remains open
   - assert close/backdrop and `Öppna Regler` still close intentionally
2. Add matching guest-shell coverage where the same watcher pattern exists in
   `ClassroomPlannerGuestWorkspaceShell.spec.ts`.
3. Refactor the shell watchers in `PlannerWorkspaceShell.vue` and
   `ClassroomPlannerGuestWorkspaceShell.vue` so settings close only on stable
   workspace-identity changes:
   - `initialView`
   - resolved draft kind
   - resolved template/context id
   - selected workspace mode
4. Avoid watcher sources that return fresh arrays or objects on every run.
   Prefer named computed keys or separate primitive watch sources with previous
   value comparison.
5. Tighten `PlannerGroupingSettingsDrawer.vue` and
   `PlannerSeatingSettingsDrawer.vue` dialog semantics if needed:
   - `role=\"dialog\"`
   - `aria-modal=\"true\"`
   - labelled heading
   - Escape closes
   - backdrop/outside click closes
   - internal controls do not close
6. Keep `openRules()` as an intentional close-and-navigate path.

## Current Frontend Entry Points

- Authenticated shell watcher/lifecycle:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Guest/public shell watcher/lifecycle:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- Grouping settings panel:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingSettingsDrawer.vue`
- Seating settings panel:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingSettingsDrawer.vue`
- Smart setting state mutation:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts`
- Toolbar affordance entry points:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
  and
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- Retained live proof:
  `scripts/playwright_pr_0287_smart_settings_persistence.py`

## Implementation Summary

Implemented as a frontend lifecycle fix:

- `PlannerWorkspaceShell.vue` now closes Smart settings from a stable workspace
  identity key instead of a fresh array watcher source, so same-identity draft
  flag replacement no longer closes the panel.
- `ClassroomPlannerGuestWorkspaceShell.vue` now uses the same stable-key pattern
  across resolved view/template context, preserving guest/public parity.
- `PlannerGroupingSettingsDrawer.vue` and `PlannerSeatingSettingsDrawer.vue`
  now expose dialog semantics, labelled headings, backdrop test ids, and Escape
  close handling while keeping internal controls non-closing.
- `PlannerSmartSettingsDrawer.spec.ts`,
  `PlannerWorkspaceShell.spec.ts`, and
  `ClassroomPlannerGuestWorkspaceShell.spec.ts` lock the persistence behavior.
- `scripts/playwright_pr_0287_smart_settings_persistence.py` proves the live
  authenticated local-dev path.

## Verification

- `pdm run fe-test -- --run PlannerWorkspaceShell ClassroomPlannerGuestWorkspaceShell PlannerSmartSettingsDrawer`
  passed: 5 files / 48 tests.
- `pdm run pytest -q tests/unit/scripts/test_playwright_script_surface.py`
  passed: 3 tests.
- `pdm run python -m scripts.playwright_pr_0287_smart_settings_persistence --start-backend --start-vite`
  passed and wrote screenshots under
  `.artifacts/playwright-pr-0287-smart-settings-persistence/`.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run lint` passed.

## Test Plan

- `pdm run fe-test -- --run PlannerWorkspaceShell ClassroomPlannerGuestWorkspaceShell`
- `pdm run fe-test -- --run PlannerGroupingWorkspacePane.export PlannerSeatingWorkspacePane.export`
  if toolbar composition assertions are touched.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Live/browser proof covering:
  - seating Smart settings open, `Historik` toggle, panel remains open
  - grouping Smart settings open, internal settings interaction, panel remains
    open
  - explicit close/backdrop/Escape closes
  - `Öppna Regler` closes because navigation is intentional

## Rollback Plan

Restore the current shell watcher behavior. Rollback is frontend-only because
this slice does not alter draft persistence, Smart settings contracts, or
backend state.

## References

- Parent primitive story:
  [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Prior dense busy-feedback slice:
  [PR-0281](pr-0281-st-29-11-toolbar-processing-spinner-and-status-pill-removal.md)
- Current toolbar distribution slice:
  [PR-0286](pr-0286-st-29-11-share-export-affordance-consolidation.md)
