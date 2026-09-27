---
type: story
id: ST-SKRIPT-40-01
title: Converge tokens, components and action buttons onto the shared package
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-40
acceptance_criteria:
- Skriptoteket's design-system map adopts tokens, tailwind-theme, the horizontal logo, dense-tool-primitives, the dense action, icon and status buttons, the segmented toggle, SystemMessage, ToastHost, the Vue barrel and action-buttons, and a sync from skill-repository main changes no file
- No Skriptoteket feature is lost, because the modal surface, secondary tone, busy spinner, surface helpers, equal-width toggle, dismissible system messages and inline buttons render from the shared package
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Skriptoteket adopts the shared tokens, Tailwind theme, horizontal logo, dense
tool primitives, dense action, icon and status components, segmented toggle,
SystemMessage, ToastHost, Vue barrel and action buttons through
`design-system sync`. Before adoption, one skill-repository release promotes
every Skriptoteket extension this slice needs into the package and syncs
HuleEdu, so no Skriptoteket feature is lost and HuleEdu call sites keep
working. The glyph exports stay null until ST-SKRIPT-40-02.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md` (D1-D13, D15-D16).
- Prerequisite in skill-repository: TASK-SKILL-REP-0186 (package release with
  the promotions and the HuleEdu sync).
- Canceled predecessor: TASK-SKRIPT-REP-0033, continued as
  TASK-SKRIPT-40-01-01.

## Tasks

| Order | Task                | Outcome                                                                       |
| ----- | ------------------- | ----------------------------------------------------------------------------- |
| 0     | TASK-SKILL-REP-0186 | Package release with all Story A promotions; HuleEdu synced (skill-repository) |
| 1     | TASK-SKRIPT-40-01-01 | Map, validate command and hook; tokens, theme and logo adopted through sync  |
| 2     | TASK-SKRIPT-40-01-02 | Dense components, segmented toggle, SystemMessage, ToastHost, barrel adopted |
| 3     | TASK-SKRIPT-40-01-03 | Action buttons adopted; inline `.btn-*` rules removed from `main.css`        |

## Verification

- A sync from skill-repository main against Skriptoteket changes no file and
  its validate command passes.
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, covering the planner, the share panel, modals and drawers,
  toasts and system messages.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | The modal surface tokens, `secondary` tone, busy spinner props, surface helpers, equal-width toggle, SystemMessage dismiss and v-model, and inline buttons are promoted in one package release. |
| D2  | ToastHost is the package component fed by a local wrapper around Skriptoteket's toast store.                                                             |
| D3  | SystemMessage keeps the package `tone` and slot API; Skriptoteket renames `variant` to `tone`.                                                            |
| D4  | Adopted files keep their current Skriptoteket paths; the map sits at the repository root.                                                                 |
| D5  | Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches.                                                                                                                                          |
