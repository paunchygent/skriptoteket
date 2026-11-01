---
type: task
id: TASK-SKRIPT-42-01-01
title: Skriptoteket frontend holds no hardcoded colour and a lint rule refuses new ones
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
  - Every colour literal listed in ST-SKRIPT-42-01 Contract Inputs reads a --huleedu-* token, and the local ESLint rule and the palette scan refuse a hardcoded colour in a .vue, a .ts and a .css file
story: ST-SKRIPT-42-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Every colour literal in the Skriptoteket frontend outside the pinball game reads
a `--huleedu-*` token, and a local ESLint rule refuses new ones. Light rendering
stays unchanged, because each token equals its replaced literal in Ljust.

- Token mapping:
  - `#fff` on the primary, checked and disabled exam buttons becomes
    `var(--button-primary-text)`.
  - The split divider `rgb(255 255 255 / 40%)` becomes
    `color-mix(in srgb, var(--button-primary-text) 40%, transparent)`.
  - The extra `.xw-pop` ring `rgba(0,0,0,0.02)` is dropped.
  - The `.xw-radio--on` inset `#fff` becomes `var(--huleedu-surface-content)`.
  - The dialog `.scrim` `rgba(8,43,76,0.32)` becomes `var(--huleedu-overlay)`.
  - The `ExamWorkspaceImportBox.vue` fallback is dropped.
  - `bg-white` becomes `bg-[var(--huleedu-surface-content)]`, and
    `hover:bg-white/70` becomes `hover:bg-[var(--huleedu-surface-content)]/70`.
- `bg-white` in the synced files `UiSegmentedToggle.vue` and
  `denseToolPrimitives.ts` is fixed in the source package, skill-repository
  `resources/frontend-design-system/huleedu-integrated/`, released as 0.1.48
  and adopted with `design-system sync`. Copied package files in Skriptoteket
  are never edited.
- The `body.app-shell-game-mode` gradient moves from `assets/main.css` to
  `views/apps/styles/fof-shell-layout.css`.
- `frontend/eslint-rules/no-hardcoded-colour.js` scans the source text:
  - a `Program` visitor covers `.ts` and `.vue`, including `<style>` blocks;
  - a `StyleSheet` visitor under `@eslint/css` 0.14.1 with language `css/css`
    covers `.css`;
  - it reports a 3-, 4-, 6- or 8-digit `#hex`, `rgb(`, `rgba(`, `hsl(`,
    `hsla(`, and Tailwind palette colour classes including `white` and `black`;
  - it excludes `FlunkOutFrenzyView.vue`, `fof-shell-layout.css`,
    `fof-shell-panels.css`, `components/apps/flunk-out-frenzy/**` and the
    already-ignored `components/ui/shared/**`.
- `palette-scan-roots = ["frontend/apps/skriptoteket/src"]` is set under
  `[tool.repository-governance.design-system]` in `pyproject.toml`.
- Non-goals: pinball styling, new tokens, and dark rendering of anything.

## Contract Inputs

- Tokens: `src/skriptoteket/web/static/css/huleedu-design-tokens.css`.
- Literals: `views/apps/exam-workspace/examWorkspace.css` lines 60, 66, 74,
  91, 195 and 295; `ExamWorkspaceNewExamConfirmDialog.vue:82`;
  `ExamWorkspaceSaveAsDialog.vue:141`; `ExamWorkspaceImportBox.vue:223`;
  `components/ui/UiDenseToggle.vue:68`; `components/ui/UiSearchBar.vue:39-40`;
  `assets/main.css:38-43`.
- Package source: skill-repository
  `resources/frontend-design-system/huleedu-integrated/src/vue/components/UiSegmentedToggle.vue`
  and `src/vue/denseToolPrimitives.ts`. The copies in Skriptoteket are
  `components/ui/shared/components/UiSegmentedToggle.vue:297` and
  `components/ui/shared/denseToolPrimitives.ts` lines 37, 50, 56, 95 and 99.
- Lint: `frontend/apps/skriptoteket/eslint.config.js`, the rule pattern in
  `frontend/eslint-rules/no-template-ref-value.js`, and the catalog in
  `frontend/pnpm-workspace.yaml` (ESLint 9.39.2, which needs `@eslint/core`
  ^0.17).
- Palette scan: `pyproject.toml:323`, and
  `DEFAULT_PALETTE_CLASS_PATTERN` in the governance
  `design_system_consumer.py`.

## Core Vertical And Performance

Units, one junior each:

1. U1, exam workspace: replace the `examWorkspace.css` literals and the three
   dialog literals with their tokens.
2. U2a, package source, in skill-repository: fix `bg-white` in the package
   source, bump it to 0.1.48, and run `pdm run design-resources-validate`. The
   parent commits and pushes skill-repository main, because `design-system sync`
   refuses an uncommitted source package.
3. U2b, after U2a: run `design-system sync` from the committed skill-repository
   checkout, then `pdm run design-system-validate` in Skriptoteket; fix
   `UiDenseToggle.vue` and `UiSearchBar.vue`.
4. U3, after U1 and U2b: the ESLint rule with `@eslint/css` and its exclusions,
   the gradient move, and `palette-scan-roots`.

No performance concern: the rule makes one text scan per file.

## Validation

- U3: a RuleTester spec beside the rule fails a `.vue`, a `.ts` and a `.css`
  sample, each holding `#123456`, `rgba(0,0,0,.1)` or `bg-white`, and passes a
  `var(--huleedu-*)` sample. `pnpm --filter @skriptoteket/spa lint` is
  clean.
- U3: with `palette-scan-roots` set, `pdm run design-system-validate` passes,
  and it fails while a temporary `bg-white` fixture sits under `src`; the
  fixture is removed afterwards. The scan matches Tailwind palette classes
  only (`DEFAULT_PALETTE_CLASS_PATTERN`), so the pinball CSS needs no scan
  exclusion.
- U2a: `pdm run design-resources-validate` passes in skill-repository.
- U2b: `pdm run design-system-validate` passes in Skriptoteket.
- U1, U2a and U2b: the specs of the touched components pass.

## Stop Conditions

- A literal has no token equal to it in Ljust: stop and report it. Add no new
  token.
- `@eslint/css` 0.14.1 cannot be installed under the pnpm catalog, or it
  conflicts with ESLint 9.39.2.
- The rule reports a file outside the listed literals that is not a false
  positive: report the path and leave the file unchanged.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1  | A local ESLint rule refuses hex, rgb, rgba and hsl colours and Tailwind palette classes in `.ts`, `.vue` and `.css`; `palette-scan-roots` is set. |
| S4  | The pinball game and `demo.counter` get no dark variant; their files are excluded from the rule.                                                  |
| X1  | The game-mode gradient moves from `main.css` to `fof-shell-layout.css`.                                                                           |
| X2  | One text-scanning rule `no-hardcoded-colour.js`, with `@eslint/css` 0.14.1 for `.css`, excludes the pinball paths and `components/ui/shared/**`.  |
| X3  | `palette-scan-roots = ["frontend/apps/skriptoteket/src"]` is set.                                                                                 |
| X4  | Synced package `bg-white` is fixed at the source, released as 0.1.48, and synced.                                                                 |
| X5  | Literals map to the tokens listed in the Implementation Contract.                                                                                 |
