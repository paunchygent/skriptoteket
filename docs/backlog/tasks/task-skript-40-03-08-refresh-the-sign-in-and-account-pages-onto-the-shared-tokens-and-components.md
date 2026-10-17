---
type: task
id: TASK-SKRIPT-40-03-08
title: Refresh the sign-in and account pages onto the shared tokens and components
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer (Sol) review 767baa2c approved without findings in the retained session 01a149c9-5bc7-7713-ba64-12dee0470bdd, evidence/reviews/TASK-SKRIPT-40-03-08/review-767baa2c.md. Closed on approved review plus unit proof under the user''s 2026-10-17 rule that parent walks cover only the exam converter. The parent authorized closure.'
task_kind: story
acceptance_criteria:
  - The sign-in, account and system pages (sign-in, provisioning, account lifecycle, forbidden, route recovery and the curated-app hosts) render with the shared tokens, action buttons and components and no hard offset shadows, keep their layout, and pass a browser walk at phone, tablet and desktop widths
dependencies:
  - TASK-SKRIPT-40-01-02
  - TASK-SKRIPT-40-01-03
story: ST-SKRIPT-40-03
backlog_document_profile: contract-derived
---

## Implementation Contract

The sign-in, account and system pages keep their layout and move onto the shared package that
ST-SKRIPT-40-01 adopted. Paths are under `frontend/apps/skriptoteket/src/`.

Screens and folders:

- Sign-in (`/auth/login`, `/auth/callback`): `views/AuthLoginView.vue` and
  `components/auth/`.
- Provisioning (`/auth/provisioning-required`):
  `views/AuthProvisioningRequiredView.vue`.
- Account lifecycle (`/forgot-password`, `/register`, `/reset-password`,
  `/verify-email`): `views/AuthLifecycleHandoffView.vue`.
- Forbidden (`/forbidden`): `views/ForbiddenView.vue`.
- Route recovery (`/public/:appId` and every unmatched path):
  `views/RouteRecoveryView.vue`.
- Curated-app hosts: `views/AppHostView.vue` (`/apps/:appId`),
  `views/PublicAppHostView.vue` (`/public/apps/:appId` and
  `/public/apps/:appId/:publicCapabilitySlug`) and
  `views/CuratedAppHostSurface.vue`, the loading, error and fallback surface
  both hosts render. `views/AppDetailView.vue`, the fallback page the
  authenticated host mounts, belongs to TASK-SKRIPT-40-03-01.

What changes:

- Colours, surfaces, borders and type use the shared tokens through
  token-mapped utilities or CSS variables.
- Every button renders from the package action-button stylesheet adopted by
  TASK-SKRIPT-40-01-03 or from a shared dense button component in
  `components/ui/shared/`. Local button styling and local
  overrides of the `.btn-*` classes go.
- Where the area hand-rolls a control that the shared subtree exports (dense
  action, icon and status components, spinner, segmented toggle,
  SystemMessage), it uses the shared component.
- Panels, cards and surfaces carry no hard offset shadow and no heavy frame:
  flat surfaces use hairline borders, floating layers the soft shadow-md, and
  press and hover feedback is colour only.

What stays: the placement and order of every element, the breakpoints and the
workflow.

The shared sync map keeps the `auth-lifecycle` resource null (ST-SKRIPT-40-01);
this task changes tokens, buttons, components and surfaces only.

Out of scope: `components/layout/` (the shell) and the exam workspace, both ST-SKRIPT-40-04; the HuleEdu-owned sign-in ceremony.

Coordination: no in-progress UI task is recorded for this area. This area is
frozen only while its refresh pair works on it.

## Contract Inputs

- ST-SKRIPT-40-03 terms G6, G7, G9, G11, G12, G29, S1 and S7.
- TASK-SKRIPT-40-01-02 (shared Vue subtree and the 0.1.24 sync with the local
  shadow sweep) and TASK-SKRIPT-40-01-03 (package action buttons).
- `huleedu-ui-design` for the panel, card, button and token treatment;
  `integrated-frontend-stack` for token mechanics.
- Area facts:
  `.orchestration/context/sessions/01a1495e-8398-75be-b2da-f0b08ba11afa/evidence/discovery/planning-facts-2026-10-17.md`.

## Core Vertical And Performance

A signed-out visitor opens the sign-in page, signs in through the HuleEdu
browser session, and opens the provisioning page and each account lifecycle
page. A signed-in user opens the forbidden page, an unknown path and a curated
app; a guest opens a public curated app. Every screen has the same layout as before; buttons, panels and
status markers come from the shared package. No request or data flow changes,
and no material performance concern is identified.

## Validation

- Focused Vitest: `pdm run fe-test` with `views/AuthLoginView.spec.ts`,
  `views/AuthProvisioningRequiredView.spec.ts`,
  `views/AuthLifecycleHandoffView.spec.ts` and the specs under
  `components/auth/`, `views/AppHostView.spec.ts`,
  `views/PublicAppHostView.spec.ts` and `views/RouteRecoveryView.spec.ts`,
  updated where they assert
  removed local classes.
- `pdm run fe-type-check` and `pdm run fe-build`.
- The task evidence lists every divergence from the shared core that the area keeps, for registration when TASK-SKILL-REP-0280 lands (ST-SKRIPT-40-03 G29).
- Gate: an independent Sol review and a real browser walk (Hemma,
  `staging-walk`) of the sign-in page, the provisioning page, each account lifecycle page, the forbidden page, the route recovery page and both curated-app hosts with phone, tablet and desktop screenshots. No Opus
  step.

## Stop Conditions

- A screen cannot take a shared token, button or component without a layout
  change: stop and report to the user.
- The shared package lacks a token, button variant or component the area needs:
  report it upstream; do not patch synced files or add a local fork.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| G9  | The sign-in, account and system pages keep their layout and get the Sol 6.1 refresh onto shared tokens, buttons and components. Source: ST-SKRIPT-40-03 G9 (user 2026-10-17).                                                                                                        |
| G7  | A Sol 6.1 pair does the refresh; it is transitional work with no greenfield UI design. Source: ST-SKRIPT-40-03 G7 (user 2026-10-17).                                                                                                                                                 |
| G11 | The task starts right after TASK-SKRIPT-40-01-02 and 40-01-03 and runs in parallel with the other areas; the area is frozen only while its pair works on it. Source: ST-SKRIPT-40-03 G11 and G6 (user 2026-10-17).                                                                   |
| G12 | Gate: independent Sol review plus a real browser walk with phone, tablet and desktop screenshots; no Opus step. Source: ST-SKRIPT-40-03 G12 (user 2026-10-17).                                                                                                                       |
| S1  | Panels and surfaces leave hard offset shadows and heavy frames for the shared panel and card treatment, with one token pass for the area. Source: ST-SKRIPT-40-03 S1 (user 2026-10-12).                                                                                              |
| S7  | The 0.1.24 sync and the removal of local shadow tokens, utilities, `.btn-brutal` and press or hover-lift transforms happen in TASK-SKRIPT-40-01-02, with hairline borders, soft shadow-md on floating layers and colour-only feedback. Source: ST-SKRIPT-40-03 S7 (user 2026-10-12). |
| L5  | `ForbiddenView`, `RouteRecoveryView`, `AppHostView`, `PublicAppHostView` and `CuratedAppHostSurface`, which had no area task, join this task. Source: ST-SKRIPT-40-03 L5 (lead 2026-10-17).                                                                                          |
