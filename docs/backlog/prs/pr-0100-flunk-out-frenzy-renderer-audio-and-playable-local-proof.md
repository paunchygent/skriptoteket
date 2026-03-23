---
type: pr
id: PR-0100
title: "Flunk-Out Frenzy: renderer, audio, and playable local proof"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-02"
tags: ["frontend", "games", "rendering", "audio"]
dependencies:
  - "PR-0099"
acceptance_criteria:
  - "Pixi rendering and Howler audio are integrated into the local runtime without moving simulation ownership into Vue."
  - "The first slice uses simple, replaceable visuals and audio cues that make the app feel real without committing to final art direction."
  - "Start, Pause, Restart, and Mute work during a local 3-ball run without requiring a page reload."
  - "Live functional verification proves the local playable slice boots, runs, disposes cleanly, and does not call the backend during live play."
---

## Problem

After the shell, runtime, and table logic land, `ST-25-02` still needs one
final integration pass to feel like a real curated app rather than a headless
simulation. The runtime must render visibly, respond to audio controls, and be
verified end-to-end in the browser.

## Goal

Finish the first local playable proof for Flunk-Out Frenzy:

- render the playable table in the browser
- wire meaningful but lightweight audio feedback
- keep visuals simple and disposable until final art/design work
- perform the live route/gameplay verification required by repo policy

## Non-goals

- No final themed art pass yet.
- No polished FX system beyond lightweight cues.
- No global high-score UI or score submission flow.
- No replay or run export.

## Implementation plan

- Add rendering and audio modules such as:
  - `PixiRenderer.ts`
  - `AudioDirector.ts`
- Use placeholder/vector rendering first, with an implementation shape that can
  later swap in real art assets and richer design work.
- Make the shell controls operational against the integrated runtime:
  - Start
  - Pause
  - Restart
  - Mute
- Keep runtime audio/browser-unlock handling explicit through the shell start
  interaction.
- Add a live browser check for:
  - route load
  - runtime mount
  - ball launch
  - scoring/HUD update
  - pause/restart/mute
  - route unmount/disposal

## Test plan

Automated:

- frontend tests for renderer/audio integration seams where practical
- unit tests for mute/reset/dispose behavior
- build/type/lint coverage for the integrated game surface

Manual/live:

- run backend + SPA locally
- open `/apps/games.flunk_out_frenzy`
- play a full local 3-ball run
- verify Start/Pause/Restart/Mute
- verify no page reload is needed between runs
- verify route leave/unmount does not leak canvases, audio, or listeners

Suggested commands:

```bash
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/components/apps/flunk-out-frenzy/**/*.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy src/views/apps/FlunkOutFrenzyView.vue
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build
pdm run docs-validate
```

## Rollback plan

- Remove the Pixi/Howler integration modules and focused tests.
- Fall back to the non-rendered runtime/table slice from `PR-0099` if needed.
- Keep the shell/runtime boundaries intact so a later rendering pass can be
  reintroduced safely.
