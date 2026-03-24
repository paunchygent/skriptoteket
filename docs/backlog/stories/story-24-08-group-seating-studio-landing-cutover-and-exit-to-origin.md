---
type: story
id: ST-24-08
title: "Klassrumskartan — Landing-page cutover and exit-to-origin flow"
status: ready
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
epic: "EPIC-24"
dependencies:
  - "ST-24-07"
acceptance_criteria:
  - "Given the improved resumable overview/home surface from `PR-0111` is workable, when this story ships, then the separate landing page is removed as the superseded Klassrumskartan home surface instead of being preserved through a longer compatibility phase."
  - "Given the teacher enters Klassrumskartan after the cutover, when the app loads, then the overview-first workspace flow becomes the default entry model."
  - "Given resumable continuation has already moved onto the new main page, when the cutover ships, then the superseded landing-page CTA path is removed cleanly rather than left behind as compatibility code."
  - "Given the teacher clicks `Avsluta` after the cutover, when pending autosave finishes normally, then they leave Klassrumskartan and return to the page they entered from."
  - "Given pending autosave does not finish promptly, when the teacher clicks `Avsluta`, then the app presents a clear confirmation before leaving unsaved work behind."
  - "Given the teacher entered Klassrumskartan from the dashboard, when they exit after the cutover, then they return to the dashboard; and given they entered from the catalog, when they exit, then they return to the catalog."
  - "Given the app was entered through refresh, deep link, or missing origin state, when the teacher clicks `Avsluta` after the cutover, then the app falls back to the catalog rather than trapping them inside an undefined exit path."
  - "Given the slice ships, when browser proof is run on the current SPA, then it proves the overview-first entry flow and exit-to-origin behavior without relying on the removed landing-page surface."
---

## Context

`ST-24-07` and `PR-0111` make `Översikt` and the main workspace home surface capable enough to
replace the separate landing page. This story is the clean cutover that removes the now-superseded
split-home model as soon as that replacement is workable.

The product direction for this cutover is explicit:

- no compatibility layer
- no half-migrated dual-home behavior after the cutover ships
- `Avsluta` means leave the app, not just go back to `Översikt`

## Problem

As long as the separate landing page remains after the improved overview/home replacement is ready,
Klassrumskartan still carries duplicate home semantics and unnecessary navigation complexity.

That makes the app harder to reason about and delays the UX simplification that the overview-first
direction is meant to unlock.

## Decisions

- This cutover is a big-bang removal, not a long compatibility phase.
- `PR-0111` and this story should be implemented in tandem:
  - first copy and improve the minimum resumable/home logic onto the new main page
  - then immediately remove the superseded landing page rather than maintain shared CTA state
- The teacher's entry origin must be preserved so `Avsluta` returns them to where they came from.
- If no valid entry origin is available, `Avsluta` falls back to the catalog.
- The top toggle remains the internal navigation model inside the app.
- `Avsluta` becomes the explicit leave-the-app action.

## Notes

- This story should start as soon as the new main-page resumable replacement is browser-proven; it
  should not wait behind a long duplicate CTA phase.
- The required exit-to-origin contract may touch route entry plumbing in addition to the planner
  workspace itself.
- The exit contract must explicitly cover three cases:
  - dashboard entry
  - catalog entry
  - refresh/deep-link/missing-origin fallback to catalog
- The post-cutover UI should not keep dead landing-page aliases, duplicate route state, or hidden
  fallback shells.
