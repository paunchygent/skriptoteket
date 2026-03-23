---
type: pr
id: PR-0108
title: "Flunk-Out Frenzy: runtime lazy-load and game bundle splitting"
status: ready
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-25-02"
tags: ["frontend", "games", "performance", "runtime"]
dependencies:
  - "PR-0104"
acceptance_criteria:
  - "The Flunk-Out Frenzy route shell loads before the heavy game runtime stack, and the initial route chunk no longer eagerly bundles the full Pixi/Rapier/Howler game runtime."
  - "Runtime boot still respects the `GameHost` / `GameRuntime` ownership boundary and the bootstrap-driven audio flag."
  - "The optimized route preserves the current immersive shell, controls, and live playable proof."
  - "Build output shows Flunk-Out runtime code split into clearer lazy chunks or vendor groups, with the optimization rationale documented in code/config."
---

## Problem

The current Flunk-Out Frenzy route eagerly pulls the full game runtime into the
route chunk:

- `pixi.js`
- `@dimforge/rapier2d-compat`
- `howler`
- the bespoke game runtime graph

This is why Vite currently reports a large Flunk-Out chunk during build. The
route works, but the shell and the heavy runtime are too tightly bundled.

That means:

- initial route load is heavier than necessary
- the user pays runtime cost before they have even started playing
- future game growth will make the current loading strategy increasingly costly

## Goal

Reshape the Flunk-Out route so it becomes shell-first and runtime-second:

- load the immersive shell immediately
- lazy-load the heavy runtime only when the route needs the game engine
- preserve the current game-first composition and runtime ownership boundary

## Non-goals

- No change to game rules or physics behavior.
- No visual redesign of the shell.
- No generic “all games framework” abstraction.
- No premature micro-optimization of unrelated SPA routes.

## Implementation plan

### 1. Separate shell loading from runtime loading

- [ ] Make the Flunk-Out route shell render without eagerly importing the full
      runtime stack.
- [ ] Keep `FlunkOutFrenzyView.vue` focused on:
      - bootstrap
      - shell composition
      - controls
      - settings
- [ ] Move heavy runtime loading behind a lazy boundary owned by the game host
      or a feature-local runtime loader.

Suggested solution:

- Lazy-load `GameRuntime` through an explicit async runtime factory.
- Keep the shell interactive and visually complete while the runtime is
  booting.

### 2. Lazy-load heavy game dependencies

- [ ] Ensure Pixi, Rapier, and Howler are only brought in when the runtime is
      actually being created.
- [ ] Avoid import graphs that pull these dependencies into the initial shell
      bundle by accident.
- [ ] Preserve the existing bootstrap-driven audio gating behavior.

Suggested solution:

- Use `import()` boundaries around runtime creation or feature-local loader
  modules rather than eager top-level imports from the shell layer.

### 3. Improve bundling clarity in Vite

- [ ] Review whether a small `manualChunks` strategy in
      `frontend/apps/skriptoteket/vite.config.ts` improves chunk separation for:
      - game runtime
      - renderer/vendor
      - physics/vendor
      - audio/vendor
- [ ] Add chunking config only if it follows the actual loading boundaries and
      does not become configuration-only cargo culting.

Suggested solution:

- Prefer real lazy boundaries first.
- Use `manualChunks` only to reinforce those boundaries, not to paper over an
  eagerly coupled architecture.

### 4. Reduce non-code route weight where safe

- [ ] Review the temporary Flunk-Out reference images and decide whether the
      current files should be:
      - optimized
      - resized
      - replaced later during the art pass
- [ ] If optimized now, keep the visual anchor intact.

Suggested solution:

- Treat this as a secondary gain after runtime lazy-loading, not the primary
  fix for the chunk warning.

### 5. Re-verify route behavior after optimization

- [ ] Prove the route still supports:
      - bootstrap
      - runtime boot
      - Start/Pause/Restart/Mute
      - route leave cleanup
- [ ] Record both build verification and live browser proof in
      `.agents/handoff.md`.

Suggested solution:

- Keep the same live route proof used for `PR-0100` / `PR-0104`.
- Add a short note summarizing the before/after chunking behavior.

## Test plan

Automated:

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/components/apps/flunk-out-frenzy/**/*.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy src/views/apps/FlunkOutFrenzyView.vue frontend/apps/skriptoteket/vite.config.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pnpm -C frontend --filter @skriptoteket/spa build`

Manual/live:

- Open `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Verify shell-first load still resolves into a playable runtime
- Verify Start/Pause/Restart/Mute still work
- Verify route leave still disposes the runtime cleanly
- Record artifact paths and observations in `.agents/handoff.md`

## Rollback plan

- Revert the lazy-load/chunking changes if they destabilize runtime boot or
  route hydration.
- Keep the `PR-0104` remediation boundary and current playable behavior intact
  even if chunk optimization needs to be deferred.
