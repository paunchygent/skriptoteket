---
type: story
id: ST-29-08
title: "Klassrumskartan — Shared custom tooltip system and global hover contract"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-04-01
epic: "EPIC-29"
dependencies:
  - "ST-29-11"
  - "ST-29-12"
acceptance_criteria:
  - "Given dense planner and editor controls still rely on browser-native `title` tooltips, when this enhancement ships, then the relevant shared control surfaces render through one custom tooltip system instead of inheriting browser-specific timing and styling."
  - "Given tooltip timing should be tunable globally, when the shared tooltip system ships, then open delay, close delay, and hover/focus behavior live in one shared frontend contract rather than in per-component ad hoc logic."
  - "Given shared controls must remain accessible and discoverable, when a tooltip is shown, then it supports hover and focus entry, exposes the correct `role=\"tooltip\"` / `aria-describedby` relationship, and dismisses predictably without trapping focus."
  - "Given this is an enhancement rather than a core prerequisite for the desktop-first overhaul, when EPIC-29 is sequenced, then this story is taken after the current post-core primitive and symbol tightening lane instead of delaying or reopening the shipped workspace redesign."
ui_impact: "Yes (shared tooltip affordances across dense planner/editor controls)"
data_impact: "No"
---

## Context

The current dense-tool lane still depends heavily on browser-native `title` tooltips for hover
discoverability. That keeps the implementation cheap, but it also means timing, presentation, and
 delay behavior are browser-owned rather than product-owned.

The tooltip upgrade should be treated as a separate enhancement lane. It improves the polish and
governance of shared controls, but it should not be allowed to block the main desktop-first
workspace overhaul.

## Notes

- This story is now intentionally sequenced after the post-core primitive/symbol tightening lane
  rather than after unfinished workspace-layout work.
- The first adoption target should be shared dense planner/editor controls, not every tooltip-like
  surface in the app.
- CodeMirror lint hovers, rich instructional popovers, and workflow-specific hover cards are out of
  scope unless they can consume the shared contract without widening the slice.
- `ST-29-11` and `ST-29-12` now define the remaining primitive and symbol/discoverability baseline
  that this story can later upgrade from browser-native `title` behavior to a product-owned tooltip
  surface.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Control-language reference: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Shared primitive baseline: [PR-0157](../prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md)
