---
type: pr
id: PR-0290
title: "ST-29-17 small-screen rules workspace"
status: done
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-17"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "small-screen"]
dependencies:
  - "PR-0284"
  - "PR-0155"
acceptance_criteria:
  - "Given `PR-0284` has introduced the phone mode shell, when the teacher opens `Regler` at the `EPIC-29` phone viewport, then the body renders a compact rule-authoring surface rather than the desktop rail, map, and inspector compressed side by side or stacked as equal cards."
  - "Given rules apply to the whole class, when the phone rules view renders, then that scope is shown as one low-height status row such as `Reglerna gäller hela klassen.` without repeated headings or explanatory panels."
  - "Given the teacher chooses a rule type on phone, when the tool list renders, then `Nära läraren`, `Håll isär`, and `Håll nära` appear as compact icon-supported rows with short subtitles and clear active/reachable state."
  - "Given the teacher is selecting students for a rule, when pending selection exists, then `Valda elever (n)`, `Rensa`, and per-student remove actions remain visible and touch-safe without overlapping the map or rule controls."
  - "Given relationship rules need two or more students, when the reduced authoring flow is active, then the drop/select area communicates where students are added without requiring the full desktop map and rail to remain visible at the same time."
  - "Given existing rules can be edited or deleted, when management actions are available on phone, then edit, delete, clear, and save actions appear only through compact controls, row actions, menus, or subordinate sheets."
  - "Given tablet, laptop, and desktop review widths render, when this slice ships, then the existing desktop rules workspace from `PR-0155` remains intact at full-composition widths."
  - "Given visual proof is captured, when the phone rules workspace is compared with the `Regler` panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`, then the interpretation preserves the approved hierarchy without requiring pixel-perfect recreation."
---

## Problem

The current `Regler` workspace is a desktop authoring surface: a compact tool
rail, shared map surface, and rule summary/inspector work together across a
wide layout. That is the right full-composition baseline, but on phone the same
model becomes fragile because tools, selected students, feedback, saved rules,
and map context all compete for the same narrow body.

This slice interprets only the fifth mockup screen: `Regler`.

## Goal

Define and implement the phone rules experience as a focused authoring surface:

- keep `PR-0284`'s active-mode plus `Lägen` shell as the entry control
- make rule-tool choice and pending student selection the default body
- show class-wide scope as one compact status row
- present `Nära läraren`, `Håll isär`, and `Håll nära` as compact
  icon-supported rows
- keep selected students visible with clear remove and `Rensa` actions
- make map/student selection available through a deliberate reduced flow rather
  than keeping desktop rail, map, and inspector simultaneously visible
- preserve existing desktop/laptop `Regler` behavior and smart-rule data
  semantics

## Non-goals

- No redesign of `Lägesmeny`, `Översikt`, `Grupper`, or `Sittplatser`.
- No change to smart-rule persistence, solver contracts, roster-global rule
  semantics, `Planeringskarta` / `Sittschema` projection semantics, or guest
  parity.
- No phone-only smart-rule state model.
- No new export/share behavior; `Regler` does not gain a `Dela` distribution
  surface in this slice.
- No reopening of the desktop `PR-0155` three-part rules workspace at laptop or
  desktop widths.

## Mockup Interpretation

Use the `Regler` phone panel in
`docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`
as qualitative product direction:

- the first rules-specific element should be a low-height class-scope status
  row, not another heading block
- the tool choices should read as three direct rows:
  `Nära läraren`, `Håll isär`, and `Håll nära`
- each tool row should use canonical icon support, one short subtitle, and a
  compact forward/configure affordance
- the default phone body should not show the desktop map as a squeezed canvas
  beside or beneath the tool rail
- selected students should have their own compact section with count, `Rensa`,
  per-student remove controls, and stable touch targets
- the drop/select area should communicate the current relationship-planning
  target without a helper paragraph or nested card stack
- saved-rule edit/delete management belongs in compact row actions, menus, or
  subordinate sheets, not as persistent full-width management panels
- the reduced layout should not repeat the shell title, add long helper copy,
  or frame each subsection as a nested card inside the planner shell

This is not a pixel contract. It is an authoring-priority contract: rule choice
and selected students win; map projection, saved-rule management, and detailed
editing remain reachable through subordinate reduced surfaces.

## Frontend And Design Authorities

- `agent-docs-governance`: docs-as-code authority; no production work without
  this governed PR slice.
- `integrated-frontend-stack`: Vue 3/Vite/TypeScript stack, token-driven
  styling, CSS-owned layout geometry, dense workspace verification.
- `brutalist-academic-ui`: brutalist academic doctrine; dense workspaces are
  instruments, not stacked card pages.
- `.codex/rules/045-huleedu-design-system.md`: token-first styling, no Tailwind
  default palette leakage, icon-supported dense controls, and dense-action
  primitive ownership.
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`:
  one stable shell, compact action rows, secondary context in drawers/menus,
  and mobile as deliberate reduced companion.
- `docs/backlog/prs/pr-0155-klassrumskartan-rules-workspace-dual-map-authoring-and-summary-cutover.md`:
  shipped desktop rules workspace and smart-rule authoring contract that must
  remain intact at laptop and desktop widths.
- `docs/mockups/st-29-small-screen-workspace-redesign/README.md`: approved
  mockup bundle and submission policy for this lane.

## Current Frontend Entry Points

- Rules workspace pane:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue`
- Rules tool rail:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesToolRail.vue`
- Rules map panel and canvas:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapPanel.vue` and
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`
- Rules summary/inspector:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesInspector.vue`
- Rules seat node:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesSeatNode.vue`
- Smart-rule UI state:
  `frontend/apps/skriptoteket/src/views/apps/useSmartRuleUiState.ts`
- Smart-rule presentation helpers:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRulePresentation.ts`
- Shared workspace shell:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Guest workspace shell:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- Rules tests:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.spec.ts`,
  and
  `frontend/apps/skriptoteket/src/views/apps/useSmartRuleUiState.spec.ts`

## Implementation Plan

1. Start from `PlannerRulesWorkspacePane.vue` and keep the current desktop
   `PR-0155` rail/map/inspector workspace intact at `laptop` and `desktop`
   widths.
2. Add a phone-specific rules composition that activates only below the full
   desktop-composition range established by `EPIC-29`.
3. Make rule-tool choice plus pending selected students the primary phone
   surface. Do not render the full desktop map as the default phone body.
4. Keep smart-rule state in `useSmartRuleUiState` and existing planner state
   actions. The reduced view should rearrange presentation and event routing,
   not create a separate phone rule model.
5. Preserve the three canonical tools and labels from the existing tool rail:
   `Nära läraren`, `Håll isär`, and `Håll nära`.
6. Preserve selected-student semantics: order, count, per-student removal,
   `Rensa`, commit/save, edit, and delete must route through the existing
   smart-rule actions.
7. Decide how map/student selection opens on phone. Acceptable patterns include
   a subordinate sheet, a focused map-selection step, or a compact drawer, as
   long as selected-student state remains visible and the default body stays
   tool-first.
8. Preserve `Planeringskarta` / `Sittschema` projection semantics inside the
   subordinate map-selection surface where those views remain available.
9. Keep saved-rule summaries compact. Edit/delete actions should be icon
   controls, row actions, overflow menus, or subordinate sheets rather than a
   persistent management panel.
10. Use CSS-owned layout and token-driven styles. Do not add measured viewport
    sizing, JS breakpoint duplication, hardcoded colors, or Tailwind default
    palette colors.
11. If a new phone-only rules component is clearer, keep it thin and
    prop/event-driven so `PlannerRulesWorkspacePane.vue` stays under SRP and
    file-size expectations.
12. Add focused component tests for phone scan order, class-scope status,
    rule-tool rows, selected-student visibility/removal, map-selection
    reachability, compact management actions, and desktop preservation.
13. Add live browser proof for `phone`, `tablet`, `laptop`, and `desktop`.
    Phone proof must include a screenshot compared qualitatively against the
    mockup's `Regler` panel.
14. Update `ST-29-17`, this PR task, and `.codex/handoff.md` with exact proof
    commands and artifact paths during implementation closeout.

## Test Plan

- `pdm run fe-test -- --run PlannerRulesWorkspacePane PlannerRulesMapCanvas useSmartRuleUiState PlannerWorkspaceShell ClassroomPlannerGuestWorkspaceShell`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof at:
  - `phone`: `390x844`, `Regler` reduced workspace with class-scope strip,
    three tool rows, selected-student actions, and map-selection reachability
  - `tablet`: `768x1024`, reduced companion behavior without desktop bleed
  - `laptop`: `1366x768`, existing desktop rules workspace still present
  - `desktop`: `1440x900`, existing desktop rules workspace still present

## Implementation Closeout

Implemented and verified on 2026-05-04 as the small-screen rules workspace
slice.

Key outcomes:

- Phone/tablet render compact rule-authoring rows for `Nära läraren`,
  `Håll isär`, and `Håll nära` with a strong active state and canonical
  Lucide-backed symbols.
- Phone rules opens with `Nära läraren` as the usable default target, keeps the
  student list open by default, and uses a sticky selected-students drop/select
  area so scrolling the list does not move the target away.
- The default phone body avoids the squeezed desktop map; detailed map
  projection remains part of the desktop/full-composition rules surface.
- Desktop rules rail/map/inspector composition remains intact at
  laptop/desktop widths.

Verification:

- `pdm run fe-test -- --run PlannerTopPanel PlannerClassWorkspace PlannerGroupingWorkspacePane PlannerSeatingWorkspacePane PlannerRulesWorkspacePane RoomCanvas PlannerShareExportPanel`
- `pdm run fe-test -- --run PlannerTopPanel PlannerClassWorkspace PlannerWorkspaceActionBar PlannerSeatingWorkspaceToolbar.overflow PlannerGroupingWorkspaceToolbar.overflow PlannerRulesWorkspacePane PlannerSeatingWorkspacePane.smart-rules`
- Signed local HuleEdu browser proof:
  `st-29-small-screen-remaining-proof: ok artifacts=.artifacts/st-29-small-screen-remaining-workspaces`

## Rollback Plan

Revert the phone-specific rules composition and any local reduced authoring
component while leaving desktop rules, smart-rule persistence, map projections,
solver behavior, guest parity, and workspace routing intact.
