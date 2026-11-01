---
type: task
id: TASK-SKRIPT-42-01-04
title: Every Skriptoteket page applies the stored theme before first paint and both top bars show the theme button
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-01'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The SPA head applies the huleedu_theme cookie before first paint, AuthTopBar and LandingLayout show UiThemeSelector at every width, and /theme-sample returns the server's 404 page
story: ST-SKRIPT-42-01
backlog_document_profile: contract-derived
---

## Implementation Contract

The SPA applies the stored `huleedu_theme` choice before first paint, and both
top bars carry the shared theme button, placed as on the `/theme-sample` page
approved in ST-SKILL-17-01. This is the last task of the story: from here,
production sets `data-theme` on every page.

- Head: a Vite plugin in `vite.config.ts` inlines the synced
  `src/theme/theme-head.js` as a classic `<script>` at `head-prepend` of
  `index.html` through `transformIndexHtml`, in dev and build. `index.html`
  and the synced `theme-head.js` are not edited.
- Store: `src/theme/themePreferenceStore.ts` exports one
  `ThemePreferenceStore` built from `readThemeChoice`, `applyThemeChoice` and
  `storeThemeChoice` in the synced `themePreference.ts`.
- Signed in: `AuthTopBar.vue` renders `UiThemeSelector` after Logga ut and
  before the Meny button, at every width and on immersive routes.
- Signed out: `LandingLayout.vue` renders `UiThemeSelector` after Hjälp in
  `.landing-header-actions`, at every width.
- `/theme-sample` is removed from Skriptoteket only: the `theme_sample` route
  and `_THEME_SAMPLE_PATH` in `spa_fallback.py`, the `themeSample` Vite input,
  and the consumer-owned `theme-sample-entry.ts` and `theme-sample.css`. The
  synced sample files stay adopted in `design-system-map.json`, because sync
  owns them and ST-SKILL-17-01 keeps the page as the shared reference.
- Non-goals: changes to synced `components/ui/shared/**` or `src/theme/`
  files other than the two deletions, and new tokens.

## Contract Inputs

- Head script: `frontend/apps/skriptoteket/src/theme/theme-head.js`; SPA head:
  `frontend/apps/skriptoteket/index.html`; Vite config:
  `frontend/apps/skriptoteket/vite.config.ts` (input `themeSample` at line 51).
- Selector: `components/ui/shared/components/UiThemeSelector.vue`, exported
  with `ThemePreferenceStore` from `components/ui/shared/index.ts`.
- Approved placement: `ThemeSampleTopBars.vue`, selector at the right end of
  the Skriptoteket bar.
- Top bars: `components/layout/AuthTopBar.vue`, `LandingLayout.vue` and their
  specs.
- Server: `src/skriptoteket/web/routes/spa_fallback.py` lines 33 and 196-204;
  `tests/unit/web/test_spa_fallback.py` `TestThemeSampleRoute` and the
  `theme_sample_path` fixture. `/theme-sample` is not a valid SPA route, so the
  fallback returns `build_not_found_html` with 404 once the route is gone.

## Core Vertical And Performance

Units, one junior each, run in parallel with disjoint files:

1. U1, head and sample removal in the frontend: the Vite plugin, removal of the
   `themeSample` input and the header comment lines naming it, and deletion of
   `theme-sample-entry.ts` and `theme-sample.css`.
2. U2, top bars: `themePreferenceStore.ts`, the selector in `AuthTopBar.vue` and
   `LandingLayout.vue`, and their specs.
3. U3, server: remove the `theme_sample` route and `_THEME_SAMPLE_PATH`, and
   replace `TestThemeSampleRoute` with one test that `/theme-sample` returns
   the 404 page.

No performance concern: the head script is one synchronous cookie read.

## Validation

- U1: `pnpm --filter @skriptoteket/spa build` passes, and the built
  `index.html` holds the head script before any stylesheet or module script;
  no `themeSample` asset is emitted.
- U2: the `AuthTopBar` and `LandingLayout` specs assert one theme button in the
  bar; `pnpm --filter @skriptoteket/spa lint` and `typecheck` are clean.
- U3: `pdm run pytest tests/unit/web/test_spa_fallback.py` passes.

## Stop Conditions

- `transformIndexHtml` cannot inline the script before first paint in both dev
  and build.
- The selector does not fit the phone bar at 360 px beside Meny and the brand.
- Removing the Vite input breaks `design-system-validate` or `design-system sync`.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                      |
| --- | -------------------------------------------------------------------------------------------------------------------------- |
| M4  | The `/theme-sample` page approved in ST-SKILL-17-01 is the top-bar mockup; the selector sits at the right end of each bar. |
| S2  | `/theme-sample` is removed from Skriptoteket; the synced sample files stay adopted.                                        |
| X1  | A Vite plugin inlines the synced `theme-head.js` at `head-prepend`; `index.html` is unchanged.                             |
| X2  | One `themePreferenceStore` module feeds both top bars.                                                                     |
