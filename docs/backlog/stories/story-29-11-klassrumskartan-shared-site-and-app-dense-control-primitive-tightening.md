---
type: story
id: ST-29-11
title: "Klassrumskartan — Shared site/app dense-control primitive tightening"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
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

## Planned PR slices

- [PR-0195: ST-29-11 dense-control primitive contract normalization and generic menu/split behavior](../prs/pr-0195-st-29-11-dense-control-primitive-contract-normalization-and-generic-menu-split-behavior.md)
- [PR-0196: ST-29-11 planner wrapper thinning and action-surface adapter cleanup](../prs/pr-0196-st-29-11-planner-wrapper-thinning-and-action-surface-adapter-cleanup.md)
- [PR-0197: ST-29-11 editor/site adoption proof and segmented-toggle contract completion](../prs/pr-0197-st-29-11-editor-site-adoption-proof-and-segmented-toggle-contract-completion.md)

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Primitive foundation: [ST-29-01](story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- Workspace baseline already using the current primitives in practice: [ST-29-05](story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- Frontend codemap: [REF-frontend-design-system-codemap-2026-03-28](../../reference/ref-frontend-design-system-codemap-2026-03-28.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
