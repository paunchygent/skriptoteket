---
type: pr
id: PR-0098
title: "Flunk-Out Frenzy: runtime core and HUD boundary"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-02"
tags: ["frontend", "games", "runtime"]
dependencies:
  - "PR-0097"
acceptance_criteria:
  - "A browser-owned runtime core exists with a fixed-step loop, command queue, and explicit lifecycle methods such as mount, start, pause, resume, restart, and dispose."
  - "Vue receives only read-only HUD snapshots such as score, balls remaining, multiplier, and runtime status."
  - "Keyboard input is translated into runtime commands rather than directly mutating Vue state or Pixi/Rapier objects."
  - "The runtime integration preserves the immersive Flunk-Out Frenzy shell from `PR-0097` and does not reintroduce generic teacher-tool panels or visible bootstrap metadata into the main play surface."
  - "The runtime integration preserves the single-composition shell from `PR-0097`: the playfield remains the visual anchor, while controls/readouts stay attached to the game scene instead of expanding back into dashboard columns."
  - "No replay capture, replay schema, or backend calls are introduced in this PR."
---

## Problem

The first local playable slice needs a runtime backbone before any table
physics or rendering code can land safely. Without a clear command loop and HUD
projection boundary, we risk mixing shell state, game state, and future
competition concerns together.

## Goal

Introduce the runtime spine for Flunk-Out Frenzy:

- fixed-step runtime loop
- command-driven input boundary
- explicit runtime lifecycle
- read-only HUD projection back to Vue

## Non-goals

- No table-specific physics yet.
- No table rules yet.
- No full rendering or audio integration yet.
- No replay work at all in this story slice.
- No backend score submission or leaderboard logic.

## Implementation plan

- Add runtime-core modules under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/`,
  likely including:
  - `GameRuntime.ts`
  - `FixedStepRunner.ts`
  - `CommandQueue.ts`
- Define runtime commands for the first slice:
  - start
  - pause
  - resume
  - restart
  - left/right flipper press/release
  - launch press/release
- Define a minimal HUD contract that Vue can safely render without owning
  machine state.
- Preserve the immersive route shell and `GameHost.vue` boundary from
  `PR-0097`; runtime work should deepen that seam, not collapse back into
  generic Skriptoteket layout patterns.
- Keep keyboard input translation outside the simulation internals so later
  replay or score-observer work remains possible without being implemented now.
- Ensure the runtime surface stays browser-owned and does not fetch backend data
  directly.

## Test plan

Automated:

- unit tests for fixed-step runner behavior
- unit tests for runtime command handling and lifecycle transitions
- frontend tests for HUD subscription/update behavior

Manual/live:

- verify keyboard input wiring does not mutate Vue-owned state directly
- verify pause/resume/restart lifecycle transitions remain clean across route
  remounts

Suggested commands:

```bash
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/components/apps/flunk-out-frenzy/game/core/*.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts src/components/apps/flunk-out-frenzy/GameHost.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy/game src/views/apps/FlunkOutFrenzyView.vue src/components/apps/flunk-out-frenzy/GameHost.vue
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
```

## Rollback plan

- Remove the new runtime-core modules and their tests.
- Revert `GameHost.vue` to a non-runtime placeholder host if necessary.
- Keep the shell/bootstrap work from `PR-0097` intact.

## Implementation summary

- Added the browser-owned runtime spine under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/`
  with `CommandQueue.ts`, `FixedStepRunner.ts`, `GameRuntime.ts`, and
  `KeyboardInputController.ts`.
- Refit `GameHost.vue` so it mounts the runtime, forwards lifecycle controls,
  emits read-only HUD snapshots, and keeps keyboard input outside Vue state.
- Added focused unit tests for the fixed-step runner, runtime lifecycle/HUD
  boundary, keyboard-to-command translation, and host/view integration.
