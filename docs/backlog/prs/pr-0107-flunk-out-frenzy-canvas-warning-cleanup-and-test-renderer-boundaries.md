---
type: pr
id: PR-0107
title: "Flunk-Out Frenzy: canvas-warning cleanup and test renderer boundaries"
status: done
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-25-02"
tags: ["frontend", "games", "testing", "runtime"]
dependencies:
  - "PR-0104"
acceptance_criteria:
  - "Focused Flunk-Out Frenzy unit tests run without jsdom `HTMLCanvasElement.getContext()` warnings."
  - "Renderer-owning code paths are no longer booted accidentally inside jsdom unit tests; browser-level verification remains the source of truth for real Pixi/canvas behavior."
  - "If a canvas stub is introduced, it is minimal, explicit, and does not replace the protocol-first test seams already used by the host/runtime tests."
  - "The chosen approach is documented in the test setup or feature test helpers so future contributors do not regress into real Pixi boot inside jsdom."
---

## Problem

Focused Flunk-Out Frenzy frontend tests currently pass, but Vitest still emits:

- `Not implemented: HTMLCanvasElement's getContext() method`

The immediate cause is that the SPA test environment is `jsdom`, while the
Flunk-Out runtime stack includes Pixi/canvas behavior that expects a real
browser-backed canvas implementation.

This is not a production defect, but it is a test-environment quality issue:

- warnings hide signal during review
- accidental renderer coupling can creep back into unit tests
- the current setup blurs the intended line between protocol-level tests and
  browser-level render verification

## Goal

Keep Flunk-Out Frenzy unit tests honest and quiet by making the renderer
boundary explicit:

- unit tests should exercise protocol seams and fake renderers/runtime factories
- browser/Playwright checks should remain the place where real Pixi/canvas
  behavior is verified

## Non-goals

- No gameplay changes.
- No change to the visible route shell.
- No replacement of browser-level verification with fake canvas tests.
- No heavy Node-native canvas stack unless lighter boundary fixes prove
  insufficient.

## Implementation plan

### 1. Audit the remaining real-canvas test paths

- [x] Identify exactly which Flunk-Out specs still trigger real Pixi/canvas
      initialization or canvas context lookup.
- [x] Confirm whether the warning comes from:
      - runtime creation paths that still fall through to `PixiRenderer.create`
      - shared test setup
      - import-time side effects

Suggested solution:

- Trace from `GameRuntime.create()` and any remaining runtime factory defaults.
- Keep the audit small and feature-local; do not broaden into unrelated SPA
  test cleanup.

Actual result:

- The smallest reproducible path was `GameRuntime.spec.ts`.
- The warning came from import-time coupling inside `GameRuntime.ts`, which
  eagerly imported `PixiRenderer.ts` even when the spec injected a fake
  renderer and never called `GameRuntime.create()`.

### 2. Tighten renderer boundaries in unit tests

- [x] Ensure all Flunk-Out unit/component specs that do not explicitly test
      real renderer behavior use fake `RuntimeRenderer` or injected
      `runtimeFactory` seams.
- [x] Remove any remaining accidental dependency on Pixi boot from:
      - `GameRuntime.spec.ts`
      - host/view specs
      - future feature-local test helpers
- [x] Keep the runtime/renderer contract protocol-first.

Suggested solution:

- Prefer protocol-level fakes over global module interception.
- Treat unit tests as runtime-boundary tests, not renderer smoke tests.

Actual result:

- `GameRuntime.ts` now lazy-loads its default engine, renderer, and audio
  adapters inside `GameRuntime.create()` and `resolveRuntimeAudio()`.
- Importing `GameRuntime` in jsdom unit tests no longer imports Pixi at module
  load time, so fake renderers remain the active seam.

### 3. Add a minimal canvas-context shim only if still needed

- [x] If warnings remain after boundary cleanup, add a minimal
      `HTMLCanvasElement.prototype.getContext` shim in
      `frontend/apps/skriptoteket/src/test/setup.ts`.
- [x] Keep the shim intentionally narrow:
      - enough to silence jsdom capability noise
      - not rich enough to mask real renderer mistakes
- [x] Document why the shim exists and when it should not be used as a reason to
      boot real Pixi in unit tests.

Suggested solution:

- Return a light fake object for known context types.
- Do not try to emulate full canvas behavior in Vitest.

Actual result:

- No shim was needed after the import boundary cleanup.
- `frontend/apps/skriptoteket/src/test/setup.ts` stays unchanged so jsdom still
  fails loudly if a future spec accidentally boots real Pixi/canvas again.

### 4. Preserve browser-level renderer truth

- [x] Keep at least one live/browser verification step proving the real route
      still boots the runtime canvas correctly after the cleanup.
- [x] Record the browser proof in `.agents/handoff.md`.

Suggested solution:

- Use the existing local route proof workflow on
  `/apps/games.flunk_out_frenzy`.
- Do not treat the shim as a substitute for browser proof.

## Verification outcome

Automated:

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run 'src/components/apps/flunk-out-frenzy/**/*.spec.ts' src/views/apps/FlunkOutFrenzyView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts src/test/setup.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pdm run docs-validate`

Manual/live:

- Authenticated Playwright probe against `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Confirmed runtime host `data-runtime-mounted=true`, `Start` advances to
  `data-runtime-status=running`, and one runtime canvas is present
- Artifact: `.artifacts/pr-0107-live-check/flunk-out-frenzy-pr0107-dev.png`

## Test plan

Automated:

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/components/apps/flunk-out-frenzy/**/*.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts src/test/setup.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`

Manual/live:

- Open `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Verify the route still mounts the runtime canvas and reaches a playable state
- Record the proof and artifact path in `.agents/handoff.md`

## Rollback plan

- Revert only the test-boundary cleanup or canvas shim if it causes false
  positives/negatives.
- Keep the `PR-0104` DI seam and runtime error handling intact.
