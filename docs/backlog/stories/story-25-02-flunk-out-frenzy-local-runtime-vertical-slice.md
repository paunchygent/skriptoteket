---
type: story
id: ST-25-02
title: "Flunk-Out Frenzy local runtime vertical slice"
status: done
owners: "agents"
created: 2026-03-22
epic: "EPIC-25"
dependencies: ["ST-25-01", "ADR-0073"]
acceptance_criteria:
  - "Given a signed-in user opens Flunk-Out Frenzy and the app bootstrap succeeds, when they press Start, then a local 3-ball session runs inside the existing SPA with one active ball, two flippers, drain handling, score, and multiplier."
  - "Given a signed-in user opens Flunk-Out Frenzy, when the route resolves, then the experience shifts into a game-first shell where Skriptoteket chrome is reduced to the shared top bar and the main surface is visually dominated by the game."
  - "Given the first viewport loads, when the user sees the ready state, then the route reads as one cohesive game composition rather than a generic dashboard, with containers only where they support interaction or critical game information."
  - "Given the user pauses, restarts, or mutes the game, when those controls are used, then the runtime responds without a page reload and the app can begin a fresh run cleanly."
  - "Given the route unmounts or changes, when the view is destroyed, then the runtime disposes its canvas, timers, listeners, and audio handles without leaking browser-side state."
  - "Given the game is running, when HUD values change, then Vue renders read-only score, balls remaining, and multiplier state without owning live simulation positions or physics state."
ui_impact: "Yes (new game surface inside the bespoke app view)"
data_impact: "No (local runtime slice only)"
---

## Context

The first playable slice should prove the app-shell versus game-runtime
boundary. The user experience must already feel like a real curated app inside
Skriptoteket, but live gameplay should remain local and browser-owned.

For Flunk-Out Frenzy, "inside Skriptoteket" does **not** mean reusing the
normal academic/brutalist tool-panel presentation. Entering the game should
feel like entering the game, with only the shared top bar retained from the
platform shell.

## Notes

- Keep the runtime narrow: one table, one active ball, keyboard controls, and
  deterministic rules.
- Replay capture is out of scope for this slice.
- Prefer a local runtime architecture that future score submission can observe
  after a run finishes, rather than calling backend endpoints during live play.
- Keep bootstrap metadata and settings out of the main play surface; if shown
  at all, they should live in hidden or secondary game-native UI.
- Use real game imagery or playfield/context art as the primary visual anchor;
  decorative gradients alone are not enough.
