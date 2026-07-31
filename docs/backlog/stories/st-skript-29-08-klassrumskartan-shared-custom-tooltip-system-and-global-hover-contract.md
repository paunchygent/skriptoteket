---
type: story
id: ST-SKRIPT-29-08
title: Klassrumskartan — Shared custom tooltip system and global hover contract
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-29
acceptance_criteria:
- Given dense planner and editor controls still rely on browser-native `title` tooltips,
  when this enhancement ships, then the relevant shared control surfaces render through
  one custom tooltip system instead of inheriting browser-specific timing and styling.
- Given tooltip timing should be tunable globally, when the shared tooltip system
  ships, then open delay, close delay, and hover/focus behavior live in one shared
  frontend contract rather than in per-component ad hoc logic.
- Given shared controls must remain accessible and discoverable, when a tooltip is
  shown, then it supports hover and focus entry, exposes the correct `role="tooltip"`
  / `aria-describedby` relationship, and dismisses predictably without trapping focus.
- Given this is an enhancement rather than a core prerequisite for the desktop-first
  overhaul, when EPIC-29 is sequenced, then this story is taken after the current
  post-core primitive and symbol tightening lane instead of delaying or reopening
  the shipped workspace redesign.
retired_ids:
- ST-29-08
---

## Context

### Source: Context

The current dense-tool lane still depends heavily on browser-native `title` tooltips for hover
discoverability. That keeps the implementation cheap, but it also means timing, presentation, and
 delay behavior are browser-owned rather than product-owned.

The tooltip upgrade should be treated as a separate enhancement lane. It improves the polish and
governance of shared controls, but it should not be allowed to block the main desktop-first
workspace overhaul.

## Epic Contract Slice

The independently reviewable behavior is represented by the source context, goal, and implementation material above.

## ADR Coverage

No separate ADR coverage was recorded in the source snapshot.

## Contract Inputs

### Source: References

- Epic parent: [EPIC-SKRIPT-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Control-language reference: [REF-SKRIPT-GENERAL-shared-tool-control-language-and-primitive-matrix-v1](../../reference/ref-shared-tool-control-language-v1.md)
- Workspace doctrine: [REF-SKRIPT-GENERAL-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Shared primitive baseline: [PR-0157](../prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md)

## Live Verification Plan

Verification follows the acceptance and verification material recorded above.

## Non-Goals

No separate non-goals were recorded in the source snapshot.

## Notes

### Source: Notes

- This story is now intentionally sequenced after the post-core primitive/symbol tightening lane
  rather than after unfinished workspace-layout work.
- The first adoption target should be shared dense planner/editor controls, not every tooltip-like
  surface in the app.
- CodeMirror lint hovers, rich instructional popovers, and workflow-specific hover cards are out of
  scope unless they can consume the shared contract without widening the slice.
- `ST-SKRIPT-29-11` and `ST-SKRIPT-29-12` now define the remaining primitive and symbol/discoverability baseline
  that this story can later upgrade from browser-native `title` behavior to a product-owned tooltip
  surface.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Story Closeout Review

No separate closeout review was recorded in the source snapshot.
