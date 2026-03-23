---
type: pr
id: PR-0097
title: "Flunk-Out Frenzy: playable shell host and runtime lifecycle"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-02"
tags: ["frontend", "spa", "curated-apps", "games"]
dependencies:
  - "PR-0096"
acceptance_criteria:
  - "`FlunkOutFrenzyView.vue` remains the top-level bespoke app shell and owns bootstrap loading, top-level loading/error states, and shell controls."
  - "Once the user enters Flunk-Out Frenzy, the app surface switches into an immersive game mode: Skriptoteket chrome is reduced to the top bar, while the game shell itself becomes fully game-themed rather than academic/brutalist."
  - "The first viewport reads as one staged game composition, not as a generic dashboard; container styling is used only for actual interaction clusters or critical game readouts."
  - "A dedicated `GameHost.vue` mounts and disposes a browser-owned runtime host without putting simulation state into Vue."
  - "The first shell exposes Start, Pause, Restart, and Mute controls without introducing leaderboard or score-submission UI, and these controls live inside the game-themed shell instead of a generic side panel."
  - "Route unmount or change disposes host-owned timers, listeners, canvas handles, and audio/runtime references cleanly."
---

## Problem

`ST-25-02` starts with an architectural boundary problem before it becomes a
gameplay problem: the bespoke Flunk-Out Frenzy shell needs a dedicated place to
mount a local browser runtime without letting Vue become the simulation owner.

If we skip this seam and build directly inside the view, the first playable
slice will be harder to test, harder to replace visually, and harder to evolve
toward future high-score flows.

## Goal

Create the first playable shell boundary for Flunk-Out Frenzy:

- keep bootstrap and app-level state in the shell view
- make the game route feel like entering the game, not entering another generic tool panel
- introduce a dedicated game host component for runtime mounting
- expose only the minimum shell controls needed for the local vertical slice
- guarantee clean runtime disposal on route teardown

## Non-goals

- No physics or scoring logic yet.
- No Pixi/Rapier/Howler integration yet.
- No leaderboard, profile, or global high-score UI.
- No replay capture or replay persistence.
- No visible bootstrap/debug metadata panels in the main game surface.

## Implementation plan

- Keep
  `frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.vue` as the
  top-level shell.
- Introduce an **immersive game route mode** in the authenticated layout so the
  left sidebar and generic content framing disappear while the shared top bar
  remains available.
- Add
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/GameHost.vue`
  as the runtime mounting boundary.
- Keep shell responsibilities explicit:
  - bootstrap loading
  - loading/error/ready rendering
  - immersive game-themed presentation
  - Start/Pause/Restart/Mute controls
  - read-only HUD projection placeholders
- Keep visible shell chrome game-native:
  - a single staged machine composition with the playfield as the visual anchor
  - game-native overlays/cards only where they support real interaction or
    critical readouts
  - settings/debug information hidden behind a secondary affordance rather than
    occupying the main screen
- Keep `GameHost.vue` responsibilities explicit:
  - own the runtime host element
  - mount/unmount the runtime
  - subscribe/unsubscribe to HUD updates
  - translate shell control clicks into runtime commands
- Follow the existing bespoke curated-app shell pattern rather than inventing a
  generic game-shell abstraction.

## Test plan

Automated:

- frontend tests for `FlunkOutFrenzyView.vue` bootstrap/control states
- frontend tests for `GameHost.vue` mount/unmount and control delegation

Manual/live:

- run backend + SPA locally
- open `/apps/games.flunk_out_frenzy`
- verify the shell reaches ready state
- verify the game host area appears in an immersive game shell and
  Start/Pause/Restart/Mute controls render without visible generic side panels
- verify route change/unmount does not leave duplicate canvases or controls

Suggested commands:

```bash
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/FlunkOutFrenzyView.spec.ts src/components/apps/flunk-out-frenzy/GameHost.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/FlunkOutFrenzyView.vue src/components/apps/flunk-out-frenzy/GameHost.vue src/views/apps/FlunkOutFrenzyView.spec.ts src/components/apps/flunk-out-frenzy/GameHost.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build
```

## Rollback plan

- Remove `GameHost.vue` and its tests.
- Remove the shell control surface additions from `FlunkOutFrenzyView.vue`.
- Keep the bespoke app route and bootstrap contract from `ST-25-01` intact.
