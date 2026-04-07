---
type: story
id: ST-29-11
title: "Klassrumskartan — Shared site/app dense-control primitive tightening"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-06
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-05"
acceptance_criteria:
  - "Given dense controls now exist across overview, grouping, seating, rules, editor, and other tool-grade SPA surfaces, when this follow-on ships, then repeated control families use one shared primitive contract instead of surface-owned variants or wrapper-specific visual rules."
  - "Given shared dense controls still rely on local CSS overrides or toolbar-owned spacing, radius, disabled, focus, active, and disclosure behavior, when this story ships, then those rules live in the shared primitive layer and surface wrappers become thin adapters."
  - "Given planner/editor/tool surfaces still expose overlapping icon-button, menu-button, split-button, toggle, or segmented-switch abstractions, when this story is complete, then the remaining wrappers are intentional usage adapters rather than accidental competing sources of truth."
  - "Given browser proof is run on the current dense-control surfaces at the canonical `laptop` and `desktop` review widths, when this story is reviewed, then control rhythm and interaction polish stay consistent without reopening the shipped workspace layouts."
ui_impact: "Yes (shared dense-control primitives across planner/editor/app surfaces)"
data_impact: "No"
---

## Context

The desktop-first workspace overhaul is now largely represented by shipped layout behavior. What
remains is not another pass on overview/grouping/seating composition. The remaining gap is the
shared primitive layer that those surfaces depend on.

This story isolates the follow-on primitive-tightening work as a cross-surface design-system lane
instead of treating it as unfinished planner-layout implementation.

## Notes

- This is a post-core tightening story, not a feature-expansion or workflow-redesign story.
- The target is shared site/app primitive governance across Klassrumskartan and adjacent dense tool
  surfaces, not one more local planner toolbar pass.
- `ST-29-01` is now the shipped foundation story. This story picks up the still-open consolidation
  and adapter-thinning work that no longer belongs under the old `PR-0158` seating-first framing.
- Bounded planner shell/layout corrections are still allowed here when they restore the existing
  `ST-29-03` / `ST-29-05` desktop contract, but that restoration work must keep planner geometry
  CSS-owned and must not reopen the accepted workspace direction through new runtime sizing or
  breakpoint logic.

## Planned PR slices

- [PR-0195: ST-29-11 dense-control primitive contract normalization and generic menu/split behavior](../prs/pr-0195-st-29-11-dense-control-primitive-contract-normalization-and-generic-menu-split-behavior.md)
- [PR-0196: ST-29-11 planner wrapper thinning and action-surface adapter cleanup](../prs/pr-0196-st-29-11-planner-wrapper-thinning-and-action-surface-adapter-cleanup.md)
- [PR-0197: ST-29-11 editor/site adoption proof and segmented-toggle contract completion](../prs/pr-0197-st-29-11-editor-site-adoption-proof-and-segmented-toggle-contract-completion.md)
- [PR-0224: ST-29-11 desktop-first planner width stability and shrink-to-fit remediation](../prs/pr-0224-st-29-11-desktop-first-planner-width-stability-and-shrink-to-fit-remediation.md)
- [PR-0225: ST-29-11 desktop-first planner toolbar priority and overflow hardening](../prs/pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md)
- [PR-0226: ST-29-11 shared planner shell parity and grouping viewport-height stabilization](../prs/pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md)
- [PR-0227: ST-29-11 exact two-row grouping board height contract at desktop baseline](../prs/pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md)
- [PR-0228: ST-29-11 follow-up: desktop student-pool rail stickiness restoration](../prs/pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md)
- [PR-0229: ST-29-11 follow-up: desktop-first planner toolbar breakpoint overflow escalation and undo/redo shortcut parity](../prs/pr-0229-st-29-11-desktop-first-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md)

## Implementation Summary (as of 2026-04-06)

- `PR-0224`, `PR-0225`, `PR-0226`, and `PR-0227` are now implemented as the current
  planner-focused `ST-29-11` hardening set: the desktop shell stays width-stable, toolbar actions
  now respect the shared overflow/priority contract, guest and authenticated grouping/seating
  shells now share the same sticky wrapper/layout contract, the grouping workspace keeps the
  explicit `480px` desktop lane floor with `56px` / `112px` group-card sizing, fresh grouping
  drafts now seed 4 groups in both guest and authenticated mode, grouping autosave preserves the
  overview-selected classroom, and the default 4-card desktop grouping board now proves exact
  `480px` two-row math at `1440x900` while populated cards retain a desktop `234px` minimum-height
  floor and can grow without forced internal scrolling.
- `PR-0228` is now closed as the bounded student-pool/class-list rail follow-up after the latest
  planner shell tightening. The canonical sticky rail contract is still explicitly owned by
  `ST-29-03` and reinforced by `ST-29-05`, while this slice closes the regression-restoration lane
  on the healthier CSS-owned baseline: the main page/workspace scroll is back, the large top panel
  can scroll away, the toolbar becomes the sticky working band, grouping/seating share the same
  `480px` rail pattern, the retained live browser proof stays on the authenticated real-data path,
  and guest/auth parity is carried by the shared shell implementation plus focused guest/auth shell
  specs.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Primitive foundation: [ST-29-01](story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- Workspace baseline already using the current primitives in practice: [ST-29-05](story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- Frontend codemap: [REF-frontend-design-system-codemap-2026-03-28](../../reference/ref-frontend-design-system-codemap-2026-03-28.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
