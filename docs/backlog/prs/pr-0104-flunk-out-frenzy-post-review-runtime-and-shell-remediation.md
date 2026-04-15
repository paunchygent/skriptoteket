---
type: pr
id: PR-0104
title: "Flunk-Out Frenzy: post-review runtime, shell, and test remediation"
status: done
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-25-01"
  - "ST-25-02"
tags: ["frontend", "games", "review", "remediation"]
dependencies:
  - "PR-0100"
acceptance_criteria:
  - "Runtime boot failures are surfaced to the user with a visible game-shell error state instead of leaving an inert cabinet."
  - "Audio mute state is lifecycle-safe: a disposed game runtime cannot leak global Howler mute state into a later route session or other app surfaces."
  - "Bootstrap feature flags are enforced by the game shell/runtime, starting with audio gating, so the route honors its published backend contract."
  - "Flunk-Out Frenzy component tests stop depending on module-level mocking for renderer/audio creation and instead use an explicit component-level DI seam."
  - "Core runtime tests gain direct coverage for CommandQueue semantics and shared scheduler utilities are deduplicated."
  - "Low-risk cleanup items are addressed or explicitly documented, including duplicated status labeling, magic-ratio intent, redundant unmount boot-state writes, and reference-art provenance."
---

## Problem

`ST-25-01` and `ST-25-02` are implemented locally, but the post-implementation
review surfaced a focused set of remediation items around runtime lifecycle,
shell error handling, bootstrap-contract enforcement, and test seam quality.

The slice is directionally correct, but these issues should be closed before
the next competition/high-score story builds on top of the current runtime.

## Goal

Harden the Flunk-Out Frenzy local slice so that:

- route/runtime failure states are honest and user-visible
- runtime-owned audio is lifecycle-safe
- backend bootstrap flags actually govern the game client
- tests use explicit seams instead of module-resolution interception
- core timing/input infrastructure has direct, durable coverage

## Non-goals

- No new gameplay mechanics.
- No art-direction overhaul or final asset pass.
- No leaderboard submission or official-score backend flow yet.
- No redesign of the competitive-games roadmap beyond this remediation pass.

## Review reconciliation

One earlier review observation is already resolved and should not be reopened as
an issue in this PR:

- `.codex/handoff.md` now includes Flunk-Out Frenzy verification commands and
  live browser proof entries for `PR-0094` through `PR-0100`.

This remediation task focuses only on the still-open issues below.

## Implementation plan

### 1. Runtime boot-failure surface

- [x] Add a visible runtime initialization error state in
      `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/GameHost.vue`.
- [x] Emit or expose boot failure to
      `frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.vue` so the
      route can disable or hide misleading controls when runtime creation fails.
- [x] Ensure the play shell distinguishes:
      - bootstrap failure
      - runtime boot failure
      - normal ready/running states
- [x] Add component tests that force `GameRuntime.create()` to reject and prove
      the failure is visible and actionable.

Suggested solution:

- Add a component-level error ref or `runtime-error` event from `GameHost`.
- Render a dedicated game-shell failure message instead of only logging to the
  console.

### 2. Global mute lifecycle safety

- [x] Fix
      `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/audio/AudioDirector.ts`
      so mute state does not leak across runtime disposal.
- [x] Ensure a new route/session starts with audio state consistent with the HUD.
- [x] Confirm disposal cleans up Howler state safely if the user leaves the
      route while muted.
- [x] Add regression tests covering:
      - mute -> dispose -> new runtime
      - muted and unmuted starts

Suggested solution:

- Treat mute ownership explicitly at runtime creation/disposal, or stop using
  global `Howler.mute(...)` as if it were route-local state.

### 3. Bootstrap contract enforcement

- [x] Thread bootstrap feature flags from
      `frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.vue` into
      `GameHost.vue` / `GameRuntime.ts`.
- [x] Start with enforcing `audio_enabled`.
- [x] Gate audio subsystem creation and shell audio affordances when disabled.
- [x] Confirm future flags can follow the same pattern without redesign.
- [x] Add tests proving the runtime/shell behavior changes when
      `audio_enabled` is `false`.

Suggested solution:

- Add explicit host/runtime options derived from bootstrap instead of treating
  feature flags as display-only metadata.

### 4. Test seam remediation: remove module-level mocking

- [x] Add an explicit DI seam to
      `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/GameHost.vue`
      for runtime creation or runtime adapter factories.
- [x] Update:
      - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/GameHost.spec.ts`
      - `frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.spec.ts`
      so tests pass fakes via the seam rather than `vi.mock(...)` on module imports.
- [x] Keep protocol-driven fake implementations for runtime/renderer/audio.

Suggested solution:

- Add an optional `runtimeFactory` prop or equivalent injected creation seam
  that defaults to `GameRuntime.create`.

### 5. Core runtime test coverage tightening

- [x] Extract shared manual scheduler logic into a reusable test helper for:
      - `GameRuntime.spec.ts`
      - `FixedStepRunner.spec.ts`
- [x] Add a new direct spec file for
      `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/CommandQueue.ts`
      covering:
      - push
      - drain
      - clear
      - repeated drain after emptying
- [x] Keep test helpers small and local to the feature tree.

Suggested solution:

- Add a shared `testScheduler.ts` in the game-core test area and import it from
  both specs.

### 6. Low-risk cleanup and clarity follow-ups

- [x] Deduplicate status-label formatting now duplicated in:
      - `GameHost.vue`
      - `FlunkOutFrenzyView.vue`
- [x] Explain the `0.76` host/cabinet aspect ratio with a named constant or
      inline comment so it is clearly distinct from the `600 x 1200` physics
      board.
- [x] Remove the redundant unmount-time `runtimeBooting.value = true` write in
      `GameHost.vue` if it remains unused.
- [x] Clarify placeholder/reference art provenance for:
      - `reference-cabinet-scene.jpg`
      - `reference-playfield-crop.jpg`
      - related `reference-*` assets
      and rename them if they are intended to remain first-class shipped assets.

Suggested solution:

- Treat these as cleanup items within the same PR when safe, otherwise record
  any intentionally deferred art-provenance cleanup in the PR notes.

## Test plan

Automated:

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/components/apps/flunk-out-frenzy/**/*.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pnpm -C frontend --filter @skriptoteket/spa build`
- `pdm run docs-validate`

Manual/live:

- Open `/apps/games.flunk_out_frenzy`
- Verify runtime boot success still reaches a playable state
- Verify a forced runtime boot failure shows a visible error state
- Verify mute state does not leak after route leave/re-entry
- Verify audio-disabled bootstrap configuration suppresses live audio behavior
- Record the route check in `.codex/handoff.md`

## Rollback plan

- Revert only the remediation seam changes if they destabilize the playable
  slice.
- Keep the `PR-0100` runtime/render/audio ownership boundary intact even if an
  individual remediation item must be postponed.
- If necessary, ship the error-surface and mute-lifecycle fixes first, then
  follow with the DI/test cleanup in a second pass.
