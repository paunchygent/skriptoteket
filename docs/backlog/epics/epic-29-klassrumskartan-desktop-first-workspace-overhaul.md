---
type: epic
id: EPIC-29
title: "Klassrumskartan — desktop-first workspace overhaul"
status: active
owners: "agents"
created: 2026-03-28
updated: 2026-03-31
outcome: "Teachers use a denser, desktop-first Klassrumskartan workspace with a canonical symbol system, compressed shell chrome, clearer task hierarchy, and intentionally reduced mobile companion layouts without changing the planner's core logic or data contracts."
dependencies:
  [
    "ADR-0069",
    "ADR-0071",
    "ADR-0072",
    "EPIC-24",
    "EPIC-27",
    "REF-group-seating-studio-product-direction-2026-03-21",
    "REF-klassrumskartan-workspace-ui-doctrine-2026-03-28",
  ]
---

## Scope

- Apply the new workspace doctrine to Klassrumskartan as a dedicated redesign lane rather than as
  incidental polish inside export or smart-assignment work.
- Own the desktop-first redesign execution scope that was previously scattered across adjacent
  export-era hardening drafts so the planner does not carry two parallel ready redesign lanes.
- Design desktop and laptop layouts as the canonical product composition for workspace-heavy
  planner flows.
- Introduce a canonical symbol system and shared planner control primitives before deeper workspace
  layout changes.
- Compress the planner shell and remove low-value status/helper bands that delay access to the live
  work surface.
- Redesign `Översikt`, `Grupper`, `Sittplatser`, and `Regler` in paced slices that build on shared
  primitives instead of each workspace inventing its own layout language.
- Define reduced mobile companion layouts only after the desktop composition is settled.

## Out of Scope

- Changing planner domain behavior, smart-assignment contracts, export contracts, or room/roster
  persistence semantics.
- Reopening the accepted class-first workflow direction from EPIC-24.
- Treating desktop redesign as a reason to force full feature parity onto phone portrait layouts.
- Folding the entire overhaul into EPIC-26 export/import work or EPIC-27 smart-assignment work.

## Risks

- If symbol work and shell work are skipped, workspace redesigns may drift into one-off affordances.
- If mobile parity remains a hidden requirement, the desktop overhaul may collapse back into
  stacked-card compromises.
- If existing ready UX-hardening stories from EPIC-26 are implemented independently without
  reconciliation, the redesign lane could duplicate or conflict with adjacent toolbar/overview
  polish work.

## Viewport Proof Matrix

Use these named review viewports whenever EPIC-29 stories call for browser proof:

- `phone`: `390x844` reduced companion proof below the desktop composition range
- `tablet`: `768x1024` reduced companion proof aligned to the `ADR-0020` tablet breakpoint
- `laptop`: `1366x768` minimum full desktop-composition proof for teacher workspaces
- `desktop`: `1440x900` roomy full desktop-composition proof for teacher workspaces

Desktop-first Klassrumskartan composition must hold at `laptop` and `desktop`. Reduced companion
layouts may appear at `tablet` and `phone`, but they must not push stacked-card compromises back up
into the `laptop` proof width.

## Story Stack

- [ST-29-01: Canonical operation symbols and planner control primitives](../stories/story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- [ST-29-02: Workspace shell compression and low-value feedback band reduction](../stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md)
- [ST-29-03: Shared desktop workspace composition primitives](../stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- [ST-29-04: Overview hierarchy and class-first dashboard redesign](../stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md)
- [ST-29-05: Grouping and seating desktop workspace overhaul](../stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- [ST-29-06: Rules workspace rail-map-inspector rebalance](../stories/story-29-06-klassrumskartan-rules-workspace-rail-map-inspector-rebalance.md)
- [ST-29-07: Reduced mobile companion layouts and breakpoint cutover](../stories/story-29-07-klassrumskartan-reduced-mobile-companion-layouts-and-breakpoint-cutover.md)
- [ST-29-08: Shared custom tooltip system and global hover contract](../stories/story-29-08-klassrumskartan-shared-custom-tooltip-system-and-global-hover-contract.md)
- [ST-29-09: Rule visibility and tool-feedback continuity](../stories/story-29-09-klassrumskartan-rule-visibility-and-tool-feedback-continuity.md)

## Notes

- `EPIC-29` is the canonical story/task hub for the Klassrumskartan UI overhaul.
- `ST-29-08` is intentionally an enhancement follow-up after the current core `ST-29-01`..`ST-29-07`
  stack and should not delay the main desktop-first redesign sequence.
- Applicable task decomposition from the earlier EPIC-26 redesign drafts is reassigned here and
  any conflicting story-level backlog docs should be removed rather than left around as dormant
  alternatives.
- This epic requires review approval before implementation begins per the repo review workflow.

## Implementation Summary (as of 2026-03-31)

- `ST-29-02` is now implemented locally through `PR-0161`, `PR-0179`, and `PR-0180`: the planner shell is compressed, grouping and seating use detached sticky workspace toolbars that now hug the authenticated topbar seam while scrolling, low-value full-width helper/status bands are removed or localized, and recovered export completion now announces once via toast with `Mina filer` copy instead of reappearing workspace bands.
- `ST-29-09` shipped through `PR-0177`: seating no longer repeats active-rule state through a redundant pill, the room-editor tool palette now exposes clearer active-tool feedback, and grouped student cards preserve the shared smart-rule marker language after assignment.
- `ST-29-03` is now done: `PR-0128` remains the shipped split-pane/local-scroll lane, `PR-0130` remains the shipped seating-toolbar stability lane, and `PR-0129` now codifies the shared zoned `PlannerWorkspaceActionBar` contract with reusable `primary`, `context`, and `secondary` wrappers that grouping, seating, and later `ST-29-06` can share.
