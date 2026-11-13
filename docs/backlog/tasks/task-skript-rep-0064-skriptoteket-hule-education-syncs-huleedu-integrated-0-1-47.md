---
type: task
id: TASK-SKRIPT-REP-0064
title: skriptoteket.hule.education syncs huleedu-integrated 0.1.47 so its app CSS no longer carries the theme sample page
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-31'
status: proposed
closeout_review:
  record: inline
  status: approved
  reviewer: Mac skill-repository orchestrator 6b4ee548 (merge; build proof checked)
  decided_at: '2026-10-31T20:45:00Z'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: >-
    TASK-SKRIPT-REP-0064#closeout. Merged into main as dc524bae0 and deployed to production with the user's approval on 31 October 2026.
task_kind: repository
dependencies:
  - TASK-SKILL-REP-0445
acceptance_criteria:
  - After deploy, no stylesheet linked from https://skriptoteket.hule.education/ contains a `theme-sample-` selector, and https://skriptoteket.hule.education/theme-sample still renders the styled sample page.
backlog_document_profile: contract-derived
---

## Implementation Contract

Companion to skill-repository `TASK-SKILL-REP-0445` (D1, D2). Package
huleedu-integrated 0.1.47 drops `ThemeSamplePage` from the shared Vue barrel,
which every app view imports, so the app's CSS stops carrying the sample
page's 78 `theme-sample-` rules (about 16.7 kB, measured live 31Oct).

- Sync 0.1.47 with the shared `design-system sync` from the skill-repository
  main checkout at the commit that merges `TASK-SKILL-REP-0445`. Update
  `design-system-map.json` only where sync refuses because the map's export
  set disagrees with the manifest.
- `frontend/apps/skriptoteket/src/theme/theme-sample-entry.ts:20` changes from `import { ThemeSamplePage } from "../components/ui/shared";` to `import ThemeSamplePage from "../components/ui/shared/components/ThemeSamplePage.vue";`, and its header comment line that says the page comes from the shared barrel says it is imported directly.
- Production: the Skriptoteket production deploy route through `hemma-devops`, approved by the user in the orchestrator thread on
  31Oct once reviews pass.

## Contract Inputs

- skill-repository `TASK-SKILL-REP-0445` and the package README at 0.1.47.

## Core Vertical And Performance

The production build, then the deployed home page and its stylesheets. The
initial CSS shrinks by about 16.7 kB.

## Validation

- `pdm run design-system-validate` passes.
- Frontend typecheck and build pass; in the build output the CSS files the built SPA `index.html` links contain
  0 `theme-sample-` matches, and the built `theme-sample.html` still links a
  stylesheet with them.
- The existing `/theme-sample` route test still passes.

## Stop Conditions

- An app view other than the theme-sample entry imports `ThemeSamplePage`.
- The build output's app stylesheets still contain `theme-sample-`.

## Decided Contract Terms

| ID  | Decided contract term                                                                          |
| --- | ---------------------------------------------------------------------------------------------- |
| D1  | Sync huleedu-integrated 0.1.47; the theme-sample entry imports `ThemeSamplePage.vue` directly. |
| D2  | Deploy to production after reviews pass (user, 31Oct).                                         |

## Closeout

- Sync commit `7e1035333`, merge `dc524bae0` (push hook: full typecheck and tests on Hemma passed); deploy `hemma-deploy-20261031-203404` ended with its readiness gate passed.
- Build and live 31Oct: `/` links `logo-horizontal-COLkxyjE.css` (134 B, was 25,113 B) and `index-D0g9L-cr.css`, both 0 `theme-sample-`; `/theme-sample` links `themeSample-*.css` (87) and renders styled; the home page renders normally.
