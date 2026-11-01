---
type: story
id: ST-SKRIPT-42-01
title: Every skriptoteket.hule.education page renders light or dark from the shared tokens and shows the theme button
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-31"
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-42
acceptance_criteria:
  - Every skriptoteket.hule.education page, signed in or out, renders in Ljust, Midnatt or Bläck from the shared tokens, the top-bar theme button stores the choice in the huleedu_theme cookie, the room surface, share pages and code editor have dark variants, print and PDF exports stay light, and a lint rule refuses new hardcoded colours
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Every page of skriptoteket.hule.education, signed in or out, renders in Ljust,
Midnatt or Bläck from the shared `--huleedu-*` tokens, and the visitor picks
the theme from a glyph button in the top bar. This is story 3 of EPIC-SKILL-17
(skill-repository) and EPIC-SKRIPT-42 here.

- System is the default and follows the device's `prefers-color-scheme`. A pick
  of Ljust, Midnatt or Bläck is stored in the `.hule.education` cookie
  `huleedu_theme`; picking System returns to following the device.
- In scope: the core SPA (catalogue, tool pages, script outputs, admin views),
  Reagensberedning, Provhantering (conversion hub and exam workspace) and
  Klassrumskartan (room surface and share pages), plus the code editor.
- Share pages follow the stored choice, or the device when none is stored, and
  show no theme button.
- `html_sandboxed` outputs render as authored inside their iframe and stay
  light in a dark page.
- Print (`@media print`), the seating PDF, every PDF, DOCX and XLSX export and
  email stay light. They are rendered on the server without app CSS.
- `/theme-sample` is removed once every page follows the theme.
- No `.ts`, `.vue` or `.css` file under the Skriptoteket frontend holds a
  hardcoded colour, and a lint rule refuses new ones.
- Non-goals: the pinball game (`games.flunk_out_frenzy`) and the counter demo
  (`demo.counter`) stay unpublished in production and get no dark variant. The
  server's bare 404 page and the developer-only "SPA not built" message stay
  unstyled.
- Until the last task lands, production sets no `data-theme`, so every page
  stays light while the earlier tasks ship.

## Contract Inputs

- Tokens: `src/skriptoteket/web/static/css/huleedu-design-tokens.css`, design
  system 0.1.47. Dark and Midnatt rules at lines 336-470; System at line 474
  under `:root[data-theme="system"]`.
- Theme wiring that exists but runs only on `/theme-sample`: `theme-head.js`,
  `themePreference.ts`, `UiThemeSelector.vue`.
- Top bars: `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue`
  (signed in) and `LandingLayout.vue` (signed out).
- Colour literals, under `frontend/apps/skriptoteket/src/`: `assets/main.css`,
  `styles/tailwind-theme.css`, `components/ui/UiDenseToggle.vue`,
  `components/ui/UiSearchBar.vue`,
  `ui/shared/components/UiSegmentedToggle.vue`,
  `ui/shared/denseToolPrimitives.ts`, and under
  `views/apps/exam-workspace/`: `ExamWorkspaceImportBox.vue`,
  `ExamWorkspaceNewExamConfirmDialog.vue`, `ExamWorkspaceSaveAsDialog.vue`,
  `examWorkspace.css`. Pinball files are out of scope.
- Lint: ESLint covers `src/**/*.{ts,vue}`; the local rule to copy is
  `frontend/eslint-rules/no-template-ref-value.js`. The shared palette scan in
  `design_system_consumer.py` is off because `palette-scan-roots` is unset in
  `pyproject.toml`.
- CodeMirror uses `defaultHighlightStyle` with `{ dark: false }` and ignores
  `--huleedu-editor-*` and `--huleedu-syntax-*`.
- Share pages: `src/skriptoteket/web/routes/classroom_planner_share_pages.py`,
  `share_renderer.py` and `share_scene_renderer.py` with inline light palettes
  and `color-scheme: light`.
- Server routes: `src/skriptoteket/web/routes/spa_fallback.py` (`/theme-sample`
  at line 196, SPA fallback at line 207).
- Production gating of curated apps: `config.py:89`
  `CURATED_APPS_PRODUCTION_ALLOWLIST`, `registry.py:26-32`.

## Tasks

1. T1: convert every colour literal listed in Contract Inputs to tokens, and
   add a local ESLint rule that refuses hex, rgb, rgba and hsl colours and
   Tailwind palette classes in `.ts`, `.vue` and `.css`; set
   `palette-scan-roots` in `pyproject.toml`.
2. T2: CodeMirror builds its editor theme and highlight style from
   `--huleedu-editor-*` and `--huleedu-syntax-*` and follows `data-theme`
   changes without a reload.
3. T3: share renderers emit a Ljust, a Midnatt and a Bläck palette from the
   shared token values, pick one from the `huleedu_theme` cookie or, when none
   is stored, from `prefers-color-scheme`, and force light under `@media print`.
4. T4, last: run `theme-head.js` in the SPA head, place the theme button in
   `AuthTopBar.vue` and `LandingLayout.vue`, and remove `/theme-sample`.
   Gate: the user reviews a whole-screen mockup of both top bars with the
   button, in Ljust and Bläck, before T4 starts.

No walking skeleton: the story crosses no new system boundary, since the
cookie, the token CSS and the selector component already exist.

## Verification

- Walk the deployed site in a real browser in System, Ljust, Midnatt and Bläck
  at desktop and phone widths, signed in and out: the catalogue, a tool page
  with output, the editor, Reagensberedning, Provhantering, Klassrumskartan and
  a share page.
- The `huleedu_theme` cookie is written for the domain `.hule.education`, not
  for the subdomain.
- Print preview and a seating PDF export, made in Bläck, come out light.
- The lint rule refuses a hardcoded colour in a `.vue`, a `.ts` and a `.css`
  file.
- `/theme-sample` returns the server's 404 page.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | Share pages follow the stored `huleedu_theme` choice, or the device when none is stored, and show no theme button.                                |
| S2  | `/theme-sample` is removed once every page follows the theme.                                                                                     |
| S3  | `html_sandboxed` outputs render as authored in their iframe and stay light in a dark page.                                                        |
| S4  | The pinball game and `demo.counter` stay unpublished and get no dark variant; amends EPIC-SKILL-17 D3.                                            |
| S5  | The server's bare 404 page and the "SPA not built" message stay unstyled.                                                                         |
| M1  | A local ESLint rule refuses hex, rgb, rgba and hsl colours and Tailwind palette classes in `.ts`, `.vue` and `.css`; `palette-scan-roots` is set. |
| M2  | CodeMirror builds its theme and highlight style from the editor and syntax tokens and follows `data-theme`.                                       |
| M3  | Share renderers emit a palette per theme (Ljust, Midnatt, Bläck), pick it from the cookie or the device, and print light.                         |
| M4  | Tasks T1-T3 in any order, T4 last; a whole-screen mockup of both top bars gates T4.                                                               |
| M5  | Share pages give Midnatt its own palette, distinct from Bläck.                                                                                    |
