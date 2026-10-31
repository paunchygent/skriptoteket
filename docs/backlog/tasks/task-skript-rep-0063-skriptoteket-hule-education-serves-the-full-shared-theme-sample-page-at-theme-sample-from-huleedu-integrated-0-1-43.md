---
type: task
id: TASK-SKRIPT-REP-0063
title: skriptoteket.hule.education serves the full shared theme sample page at /theme-sample from huleedu-integrated 0.1.43
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-31'
status: ready
closeout_review:
  record: inline
  status: not_started
dependencies:
  - TASK-SKILL-17-01-04
task_kind: repository
acceptance_criteria:
  - skriptoteket.hule.education/theme-sample shows the 0.1.43 Vue sample page with the live selector, the frontend typecheck, lint and build pass, and production is deployed after the user approves it
backlog_document_profile: contract-derived
---

## Implementation Contract

Companion to skill-repository `TASK-SKILL-17-01-04` (story `ST-SKILL-17-01`):
skriptoteket.hule.education/theme-sample shows the full shared theme sample page from
huleedu-integrated 0.1.43, a Vue page with the live theme selector in two top
bars, buttons, panels, fields, status pills, a dialog, the room surface, a
simplified editor and pinball board, and a share page. No existing page
changes; every app screen stays light.

- Sync: run the shared `design-system sync` from the clean skill-repository
  main checkout at the commit that merges TASK-SKILL-17-01-04 (0.1.43).
- `design-system-map.json`: remove `theme-sample` (the deleted
  `themeSample.ts`); add `ui-theme-selector`, `ui-theme-sample-page`,
  `ui-theme-sample-top-bars`, `ui-theme-sample-controls`,
  `ui-theme-sample-workspaces` and `ui-theme-sample-share` beside the
  existing components in `frontend/apps/skriptoteket/src/components/ui/shared/components/`.
- `frontend/apps/skriptoteket/src/theme/theme-sample-entry.ts`: import the stylesheet that loads
  tokens, Tailwind, `brand.css` and `action-buttons.css` in the shared order
  (the app main stylesheet under `frontend/apps/skriptoteket/src/styles/`), then `createApp(ThemeSamplePage, { themePreference })`
  mounted on `#theme-sample`, where `themePreference` is
  `{ read: readThemeChoice, apply: applyThemeChoice, store: storeThemeChoice }`
  from `./themePreference`. No existing view imports the page.
- `theme-sample.html` and `theme-head.js` are unchanged in 0.1.43, so the
  `/theme-sample` route (`src/skriptoteket/web/`) and the CSP hash stay as they are.
- Production: after the user approves, the Skriptoteket production deploy route through `hemma-devops`.

## Contract Inputs

- skill-repository `TASK-SKILL-17-01-04`; package README and manifest at
  0.1.43.
- The task 1 companion of this repository, which added the route, entry,
  Vite input and CSP hash.

## Core Vertical And Performance

Browser request for `/theme-sample` on skriptoteket.hule.education, the built page mounting the
shared Vue page; the selector writes the `.hule.education` cookie. No
material performance concern.

## Validation

- `pdm run design-system-validate` passes.
- Frontend typecheck, lint and `vite build` pass, and the built
  `theme-sample.html` loads a module that contains `ThemeSamplePage`.
- The existing `/theme-sample` route test still passes.

## Stop Conditions

- Any change to an existing view or to a route other than `/theme-sample`.
- Any existing page loads `theme-head.js` or `ThemeSamplePage`.
- Production deploy before the user's approval in the orchestrator thread.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Companion terms follow skill-repository TASK-SKILL-17-01-04 D10 and M2: sync 0.1.43, map the new components, mount `ThemeSamplePage` with a store built from `themePreference.ts`. |
| C2  | Production release only after the user's approval (story D10).                                                                                                                     |
