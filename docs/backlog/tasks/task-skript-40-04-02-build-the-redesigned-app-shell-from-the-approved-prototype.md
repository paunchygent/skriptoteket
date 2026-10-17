---
type: task
id: TASK-SKRIPT-40-04-02
title: Build the redesigned app shell from the approved prototype
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Every signed-in screen renders inside the redesigned top bar, sidebar and page frame from the approved prototype at phone, tablet and desktop widths
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

An Opus builder implements the app shell from the prototype the user approved
in TASK-SKRIPT-40-04-01: the top bar, the sidebar and the page frame that every
signed-in screen renders inside, and the public page frame. It runs in
parallel with TASK-SKRIPT-40-04-03.

This task delivers:

- `AuthLayout.vue`, `AuthTopBar.vue`, `AuthSidebar.vue` and
  `LandingLayout.vue` rebuilt to the approved prototype and its design rules,
  using the shared components and buttons from TASK-SKRIPT-40-01-02 and
  TASK-SKRIPT-40-01-03.
- The shell at phone, tablet and desktop widths as the prototype shows them.
- The existing shell modes keep working: the immersive mode of the selected
  game routes and focus mode (`stores/layout.ts`).
- The Opus lead checks the built shell screens against the prototype.

Out of scope: the layout of the screens inside the shell (ST-SKRIPT-40-03),
the exam workspace (TASK-SKRIPT-40-04-03), and any backend change.

## Contract Inputs

- Story: ST-SKRIPT-40-04. Approved prototype and design rules from
  TASK-SKRIPT-40-04-01.
- Shared components and buttons: TASK-SKRIPT-40-01-02 and
  TASK-SKRIPT-40-01-03.
- Code: `frontend/apps/skriptoteket/src/App.vue`,
  `frontend/apps/skriptoteket/src/components/layout/` and
  `frontend/apps/skriptoteket/src/stores/layout.ts`.
- TASK-SKRIPT-08-36-02 (in progress) changes the same shell components to keep
  Hjälp, focus mode and logout reachable at every width; its landed outcome is
  the starting point of this build.
- Visual authority: the huleedu-ui-design skill and the shared
  huleedu-integrated tokens.

## Core Vertical And Performance

A signed-in teacher opens the home page, a tool, Klassrumskartan and the exam
workspace at phone, tablet and desktop widths, opens and closes the sidebar,
turns focus mode on and off, and opens a game route in immersive mode; every
screen renders inside the redesigned shell. A public visitor opens the landing
page inside the redesigned public frame.

## Validation

- Focused Vitest specs through `pdm run fe-test` for the shell:
  `src/components/layout/AuthLayout.spec.ts`,
  `src/components/layout/AuthLayout.actions.spec.ts`,
  `src/components/layout/AuthSidebar.spec.ts` and
  `src/components/layout/LandingLayout.spec.ts`, updated to the new shell and
  covering focus mode and the immersive route.
- `pdm run fe-type-check` and `pdm run fe-build`.
- A real browser walk of the core vertical at phone, tablet and desktop widths.
- The Opus lead's check of the built screens against the approved prototype.

## Stop Conditions

- The prototype is not approved, or TASK-SKRIPT-40-01-02 or
  TASK-SKRIPT-40-01-03 is not done.
- TASK-SKRIPT-08-36-02 is still open on the shell components when this build
  starts: report to the parent.
- The prototype does not settle a shell state the build needs: report to the
  Opus lead.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | The app shell is the top bar, the sidebar and the page frame, and it is part of the greenfield redesign; every other screen keeps its layout (user 2026-10-17, G9).                      |
| S2  | After the user approves the prototype, two Opus builders build the shell and the workspace in parallel; the Opus lead checks their screens against the prototype (user 2026-10-17, G10). |
| S3  | The shell is built from the user-approved prototype with its approved looks (sizes, colour, type) (user 2026-10-17, G1, G5).                                                             |
| S4  | The shell is frozen except for bug fixes while it is built; other areas keep shipping UI (user 2026-10-17, G6).                                                                          |
