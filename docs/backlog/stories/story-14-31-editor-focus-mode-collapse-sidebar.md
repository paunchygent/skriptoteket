---
type: story
id: ST-14-31
title: "Editor: Focus mode (collapse left sidebar)"
status: ready
owners: "agents"
created: 2026-01-04
updated: 2026-01-04
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author is in the editor, when they toggle Focus mode, then the left navigation sidebar is collapsed to maximize editor/diff width on desktop."
  - "Given Focus mode is enabled, then the setting persists across reloads (local storage)."
  - "Given Focus mode is enabled, when the user navigates to other authenticated pages, then the layout remains in the same mode (global state), but the editor remains the primary entry point for the toggle."
  - "Given Focus mode is enabled, then a clearly visible control exists to exit Focus mode so the user is never trapped."
dependencies:
  - "ST-14-18"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

This story exists to support ST-14-17/18 diff ergonomics and upcoming AI editor work where width matters.

## Implementation decisions

- Desktop only: mobile already has a hamburger/drawer; Focus mode targets desktop real-estate.
- Implement as a global layout state in `AuthLayout.vue`, persisted in local storage.
  - Persistence should be keyed by `user_id` (focus mode is global across authenticated pages, not per-tool).
- Provide an explicit toggle in the editor UI (most important) and optionally also in the top bar for discoverability.
- When collapsed:
  - Hide the desktop sidebar and remove the desktop `margin-left` reserved space.
  - Keep a persistent, obvious “Show menu” control (e.g., in the top bar) so the user can always exit Focus mode.
