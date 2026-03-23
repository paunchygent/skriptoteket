---
type: pr
id: PR-0095
title: "Flunk-Out Frenzy: bespoke route and lightweight shell"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-23
stories:
  - "ST-25-01"
tags: ["curated-apps", "frontend", "spa"]
dependencies:
  - "PR-0094"
acceptance_criteria:
  - "A signed-in user opening `/apps/games.flunk_out_frenzy` resolves to a dedicated `FlunkOutFrenzyView.vue` via the existing app host."
  - "The app host does not fall back to the generic `AppDetailView` for `games.flunk_out_frenzy`."
  - "The new bespoke view is a real shell view, but remains static/light before runtime work begins."
  - "Live route verification confirms the bespoke shell renders successfully."
---

## Problem

Even with backend registration in place, `ST-25-01` is still incomplete until
the SPA recognizes Flunk-Out Frenzy as a bespoke curated app and mounts a
dedicated view instead of the generic fallback.

## Goal

Add the first real SPA surface for Flunk-Out Frenzy:

- register the bespoke view in the existing app host
- create a lightweight shell view that future bootstrap/runtime work can attach
  to
- prove that the route behaves like a proper bespoke curated app route

## Non-goals

- No bootstrap loading yet.
- No Pixi/Rapier/Howler integration yet.
- No gameplay runtime yet.
- No score, leaderboard, or replay UI yet.

## Implementation plan

- Add `games.flunk_out_frenzy` to the bespoke registry in
  `frontend/apps/skriptoteket/src/views/AppHostView.vue`.
- Create
  `frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.vue`.
- Keep the shell intentionally light:
  - title
  - summary/loading/error placeholders
  - dedicated app layout container for the later bootstrap/runtime work
- Do not introduce dynamic component naming or backend-driven component
  resolution; follow the current hardcoded bespoke app pattern.
- Add frontend tests for route/view selection and blocking behavior.

## Test plan

Automated:

- frontend tests around `AppHostView` bespoke resolution
- view render test for the new bespoke shell

Manual/live:

- run the SPA/backend locally
- open `/apps/games.flunk_out_frenzy`
- verify the dedicated shell renders and generic fallback is not used

Suggested commands:

```bash
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/AppHostView.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/AppHostView.vue src/views/apps/FlunkOutFrenzyView.vue src/views/AppHostView.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build
```

## Rollback plan

- Remove the bespoke registry entry from `AppHostView.vue`.
- Remove `FlunkOutFrenzyView.vue` and its tests.
- The backend curated app registration can remain if needed for later work.
