---
type: pr
id: PR-0161
title: "ST-29-02: shared sticky workspace toolbar and transient feedback cutover"
status: done
owners: "agents"
created: 2026-03-29
updated: 2026-03-31
stories:
  - "ST-29-02"
tags: ["frontend", "ux", "klassrumskartan", "toolbar", "shell", "playwright"]
dependencies:
  - "EPIC-29"
  - "PR-0153"
  - "PR-0155"
  - "PR-0157"
acceptance_criteria:
  - "Given the teacher opens `Grupper` or `Sittplatser`, when the shell-compression slice ships, then the planner renders one compressed shell plus one detached shared sticky workspace toolbar immediately above the live board/canvas surface instead of separating them with helper/status bands."
  - "Given export success, ready, or other non-blocking workspace feedback occurs, when this slice ships, then it is expressed through toast/inbox behavior or compact toolbar-local status rather than a full-width interstitial band that delays the work surface."
  - "Given the teacher dismisses a completed export message, when they leave and re-enter the same workspace, then the dismissed success state does not reopen as a full-width band and the teacher is instead directed to `Mina filer` for later retrieval."
  - "Given grouping or seating needs awareness of active smart rules, when this slice ships, then that awareness is carried by toolbar-local or other compact surface-attached affordances instead of a full-width summary strip between the toolbar and the main workspace."
  - "Given `Regler` already owns the rail + map composition from `PR-0155`, when this slice ships, then the left rail stays locally sticky and the map-dominant composition is preserved rather than being flattened into the shared toolbar model."
  - "Given browser proof is run at `1366x768` and `1440x900`, when the slice is verified, then the teacher reaches `Grupper`, `Sittplatser`, and `Regler` materially earlier without regressing history, export, or rules-entry workflows."
---

## Problem

The current planner shell still reaches the live workspace too late on laptop-height screens even
after the dense-control redesign:

- `Grupper` places a full-width smart-rules summary strip between the toolbar and the group board.
- `Sittplatser` places export-status feedback and the smart-rules summary strip between the toolbar
  and the room canvas.
- completed export feedback reappears after workspace re-entry because the export flow restores a
  succeeded job for the active draft while the workspace-local dismiss state resets on remount.

That leaves the shell stable in theory but still too tall in practice.

## Goal

Ship the first ST-29-02 shell-compression slice as a focused frontend cut:

- one detached shared sticky toolbar row for `Grupper` and `Sittplatser`
- no low-value full-width helper/success bands between toolbar and live surface
- success feedback that behaves as transient product feedback rather than persistent workspace chrome
- preservation of the stronger `Regler` rail + map composition already established in `PR-0155`

## Locked design decisions

- The correct toolbar direction is the shared detached toolbar row, not per-pane local placement.
- The shared toolbar belongs directly above the live workspace surface, not below it.
- Sticky behavior applies to the shared toolbar row; `Regler` keeps its own locally sticky rail.
- Non-blocking success/ready feedback should prefer toast/inbox behavior over full-width bands.
- Export follow-up belongs in `Mina filer`; the workspace should not keep a persistent
  `Ladda ned igen` success band.
- Grouping and seating should not keep a full-width smart-rules summary strip between toolbar and
  surface merely to restate information that already lives in `Regler` or local markers.

## Non-goals

- Changing planner domain behavior, smart-assignment contracts, export artifact contracts, or
  history semantics.
- Reopening the dense-control primitive contract from `ST-29-01` unless this slice exposes a real
  missing seam.
- Mobile redesign or breakpoint cutover work from later `EPIC-29` stories.
- Rebalancing the full `Regler` composition beyond the sticky/local-rail adjustments needed to keep
  its current doctrine intact.

## Implementation plan

1. Promote the shared sticky toolbar seam into the planner shell.
   - Move the `Grupper` / `Sittplatser` action row ownership into the shell layer so the toolbar
     becomes one detached shared row immediately below the compressed shell.
   - Keep workspace-specific actions distinct through slots/zones instead of inventing a new
     generic action schema.
   - Make the shared row sticky with a stable offset that does not fight the shell.

2. Remove interstitial bands from grouping and seating.
   - Delete the full-width grouping/seating smart-rules summary strip from the area between toolbar
     and live surface.
   - Re-home compact awareness to toolbar-local context and move `Använd historik` into the seating
     toolbar instead of keeping it inside the strip.
   - Keep only truly blocking or error-class feedback in-flow, and prefer compact/local surfaces
     over page-wide bands.

3. Demote export feedback out of the workspace flow.
   - Use toast/inbox behavior for success and completed-export messaging with explicit `Mina filer`
     copy.
   - Keep progress/recovery/error states compact and local to the workspace toolbar if they need to
     stay visible during work.
   - Fix the current success-band re-entry problem by removing or persisting the relevant restored
     success surface instead of remounting it as a new full-width band.

4. Preserve the rules workspace posture.
   - Keep the `Regler` rail locally sticky.
   - Avoid reintroducing a new right-side or top-band composition that competes with the map.
   - Limit `Regler` work here to shell-compression compatibility, not a deeper composition rewrite.

5. Prove the laptop composition.
   - Add focused component coverage for shell + toolbar placement and export-feedback behavior.
   - Re-run the existing local browser proofs and manual laptop checks against the real planner.

## Coding assessment (2026-03-29)

Required verification and live checks already show the slice is real and bounded:

- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_pr_0157_dense_toolbar_check --base-url http://127.0.0.1:5173`
- `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`

Live laptop proof at `1366x768` confirms:

- `Grupper` still puts the rules summary strip between the toolbar and the board.
- `Sittplatser` still puts the export-success band and rules summary strip between the toolbar and
  the canvas.
- dismissing the seating export-success band and switching `Sittplatser` -> `Regler` ->
  `Sittplatser` reproduces the reappearance bug.

Current code seams that matter:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSmartRulesSummaryStrip.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts`

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesToolRail.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSmartRulesSummaryStrip.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts`
- `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts`
- `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts`
- `frontend/apps/skriptoteket/src/assets/main.css`

## PR-sized execution checklist

- [ ] Move grouping/seating toolbar ownership into the shared planner shell without flattening
      workspace-specific semantics
- [ ] Make the shared toolbar sticky directly above the live workspace surface
- [ ] Remove the grouping/seating full-width smart-rules summary strip from between toolbar and
      surface
- [ ] Re-home `Använd historik` and compact rules awareness into non-band surfaces
- [ ] Replace completed export success/ready bands with toast/inbox behavior and `Mina filer` copy
- [ ] Fix the export success-band re-entry behavior for the same draft/workspace state
- [ ] Keep the `Regler` rail locally sticky without regressing the map-dominant layout
- [ ] Add or update focused frontend tests
- [ ] Re-run browser proof and laptop manual verification
- [ ] Record the live UI verification in `.agents/handoff.md` if implementation proceeds

## Test plan

- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_pr_0157_dense_toolbar_check --base-url http://127.0.0.1:5173`
- `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
- Manual live proof at `http://127.0.0.1:5173/apps/classroom.group-seating-studio`:
  - verify sticky shared toolbar placement in `Grupper` and `Sittplatser`
  - verify `Regler` rail remains sticky and map-dominant
  - verify no success/ready full-width band reappears after dismissal and workspace re-entry
  - verify teachers are routed to `Mina filer` for later export retrieval

## Rollback plan

- Revert the shared-toolbar promotion and transient-feedback cutover together if the new shell
  contract proves unstable.
- If rollback is required, keep `PR-0155` and `PR-0157` intact so the rules-workspace doctrine and
  dense-control primitive layer remain the baseline.

## References

- Story parent: [ST-29-02](../stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md)
- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Dense primitive baseline: [PR-0157](pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md)
- Rules workspace baseline: [PR-0155](pr-0155-klassrumskartan-rules-workspace-dual-map-authoring-and-summary-cutover.md)
- Export-flow baseline: [PR-0153](pr-0153-klassrumskartan-shared-export-flow-composable-and-planner-hotspot-reduction.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
- Frontend skill: [skriptoteket-frontend-specialist](/Users/olofs_mba/Documents/Repos/skill-repository/skills/skriptoteket-frontend-specialist/SKILL.md)
- Browser automation rule: [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
