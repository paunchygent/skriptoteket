---
type: task
id: TASK-SKRIPT-REP-0060
title: The top bar shows the Skriptoteket logo, larger than app titles, linking to the signed-in start page
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-30'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The signed-in top bar shows logo-horizontal.svg (the BrandLogo image) on desktop, tablet and phone, with the app label beside it as today
  - The logo's visible height is larger than the H1 page title of every app view at desktop, tablet and phone, within the existing top-bar height
  - Clicking the logo goes to the page sign-in lands on when no other target was saved
backlog_document_profile: contract-derived
---

## Implementation Contract

The app shell rebuild (TASK-SKRIPT-40-04-02, `b71fd8524`, 2026-10-17) replaced the Skriptoteket logo in the
signed-in top bar with plain serif text, smaller than the app page titles. This task puts the logo back as the
home control.

- Actors: every signed-in user in the app shell; the login page keeps its logo as it is.
- Change: `AuthTopBar.vue` `.topbar-brand` renders `BrandLogo` (`/logo-horizontal.svg`) inside its RouterLink,
  with `alt="Skriptoteket"` as the link's accessible name; the app label (`.topbar-brand-app`) stays beside it.
- Size: the logo's visible height is larger than the H1 page title of every app view at desktop (>= 1280),
  tablet (768-1279) and phone (< 768), and the top bar keeps its current height. Sizes come from shared tokens.
- Link: the logo goes to the page sign-in lands on when no other target was saved. If that is not `/`, the link
  targets that route.
- Non-goals: the login page, the logo SVG itself, other top-bar actions.

## Contract Inputs

- User decisions of 2026-10-30 (Hemma orchestrator session, AskUserQuestion): restore the logo; clearly larger
  than app H1s; link to the signed-in start page.
- `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue` (`.topbar-brand` lines 87-95 and its CSS),
  `src/components/brand/BrandLogo.vue`, `src/router/routes.ts` (`home` at `/`), `src/router/index.ts` sign-in
  redirect with the preserved `next` param.
- `huleedu-ui-design` visual system: wordmark and page-title roles, tokens only.

## Core Vertical And Performance

One signed-in screen: the top bar shows the logo, taller than the app's H1, and a click lands on the signed-in
start page. No performance concern; the SVG is already served. One junior unit: the top bar markup, CSS and
its spec.

## Validation

- Vitest in the existing `AuthTopBar` / layout spec: the brand link renders the `BrandLogo` image with alt
  `Skriptoteket`, keeps the app label, and targets the signed-in start route.
- One check in production or staging on a phone and on desktop that the logo is taller than the app H1.

## Stop Conditions

- The logo cannot be taller than the app H1s without growing the top bar.
- The signed-in start page differs per role in a way one link cannot follow.

## Decided Contract Terms

| ID  | Decided contract term                                                                                             |
| --- | ----------------------------------------------------------------------------------------------------------------- |
| D1  | The signed-in top bar shows `BrandLogo` (`logo-horizontal.svg`) on every band, with the app label beside it.      |
| D2  | The logo's visible height is larger than every app H1 at desktop, tablet and phone; the top bar keeps its height. |
| D3  | The logo links to the page sign-in lands on when no other target was saved.                                       |
| D4  | Light route: one junior, focused Vitest, the user's check in production; no review.                               |
