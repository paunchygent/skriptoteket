---
type: story
id: ST-25-02
title: "Pinball Teacher local runtime vertical slice"
status: ready
owners: "agents"
created: 2026-03-22
epic: "EPIC-25"
dependencies: ["ST-25-01", "ADR-0073"]
acceptance_criteria:
  - "Given a signed-in user opens Pinball Teacher and the app bootstrap succeeds, when they press Start, then a local 3-ball session runs inside the existing SPA with one active ball, two flippers, drain handling, score, and multiplier."
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

## Notes

- Keep the runtime narrow: one table, one active ball, keyboard controls, and
  deterministic rules.
- Replay capture seams may exist in this slice, but backend replay persistence
  is out of scope here.
- Prefer a local runtime architecture that future score submission can observe
  after a run finishes, rather than calling backend endpoints during live play.
