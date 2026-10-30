---
type: task
id: TASK-SKRIPT-REP-0062
title: skriptoteket.hule.education serves the shared theme-sample page at /theme-sample from huleedu-integrated 0.1.40
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-30'
status: ready
closeout_review:
  record: inline
  status: not_started
dependencies:
  - TASK-SKILL-17-01-01
task_kind: repository
acceptance_criteria:
  - skriptoteket syncs huleedu-integrated 0.1.40 through the shared design-system sync and design-system-validate passes
  - GET /theme-sample returns the built theme-sample page and every other route behaves as before, shown by a focused route test
  - No existing page loads the theme head script, so every app screen stays light
  - The frontend typecheck and lint pass, and production is deployed through the approved route after the user approves it
backlog_document_profile: contract-derived
---

## Implementation Contract

Companion to skill-repository `TASK-SKILL-17-01-01` (story `ST-SKILL-17-01`):
skriptoteket.hule.education serves the shared theme-sample page at
`/theme-sample`, so a theme chosen there is honoured on hule.education and the
reverse. No existing page changes; every app screen stays light.

- Sync: run the shared `design-system sync` from the clean skill-repository
  main checkout at the commit that merged TASK-SKILL-17-01-01 (0.1.40); this
  also moves Skriptoteket from 0.1.38.
- `design-system-map.json`: map `theme-head`, `theme-preference`,
  `theme-sample` and `theme-sample-page` into
  `frontend/apps/skriptoteket/src/theme/` as `theme-head.js`,
  `themePreference.ts`, `themeSample.ts` and `theme-sample.html`.
- New `frontend/apps/skriptoteket/src/theme/theme-sample-entry.ts`: imports
  `../styles/tokens.css`, then calls `mountThemeSample` on `#theme-sample`.
- `frontend/apps/skriptoteket/vite.config.ts`: `build.rollupOptions.input`
  lists `index.html` and `src/theme/theme-sample.html`; the built page lands
  at `src/skriptoteket/web/static/spa/src/theme/theme-sample.html` with assets
  under `/static/spa/assets/`.
- `src/skriptoteket/web/routes/spa_fallback.py`: `GET /theme-sample`,
  declared before the catch-all, returns that built file as HTML and the
  existing 404 page when it is missing.
- Production: after the user approves, `pdm run hemma-deploy` through
  `hemma-devops`.

## Contract Inputs

- `TASK-SKILL-17-01-01` and its README `## Version 0.1.40 Changes`.
- `/static` is mounted without directory index; unmatched paths outside the
  SPA route list return a 404 page (`spa_fallback.py`); Vite builds with
  `base: "/static/spa/"` and `build.manifest`.
- Skriptoteket sets no Content-Security-Policy, so the inline head script
  needs no hash.

## Core Vertical And Performance

Browser request for `/theme-sample` on skriptoteket.hule.education, through
the route, to the built page whose inline head script reads the
`.hule.education` cookie. No material performance concern.

## Validation

- `pdm run design-system-validate` passes.
- A focused test in `tests/unit/web/test_spa_fallback.py`: `/theme-sample`
  returns the built page when present and the 404 page when missing; an
  existing SPA route still returns the SPA index.
- Frontend typecheck, lint and `vite build` pass, and the built page exists
  at the path above; the SPA index still loads its manifest assets.

## Stop Conditions

- Any change to an existing view or route other than `/theme-sample`.
- Any existing page loads `theme-head.js`.
- Production deploy before the user's approval in the orchestrator thread.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Theme files map into `frontend/apps/skriptoteket/src/theme/` beside a Skriptoteket-owned `theme-sample-entry.ts` (ST-SKILL-17-01 M3, TASK-SKILL-17-01-01 T2). |
| C2  | The page is an extra Vite input served by one route at `/theme-sample` before the catch-all (ST-SKILL-17-01 M3).                                              |
| C3  | Production deploys after the user approves (ST-SKILL-17-01 D10).                                                                                              |
