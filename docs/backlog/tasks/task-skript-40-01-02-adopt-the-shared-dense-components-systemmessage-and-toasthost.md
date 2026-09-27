---
type: task
id: TASK-SKRIPT-40-01-02
title: Adopt the shared dense components, SystemMessage and ToastHost
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The dense tool primitives, dense action, icon and status buttons, segmented toggle, SystemMessage, ToastHost and Vue barrel are adopted through sync with no local copy remaining
- SystemMessage call sites use the package tone API and toasts render through a local wrapper around the unchanged toast store
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
dependencies:
- TASK-SKRIPT-40-01-01
story: ST-SKRIPT-40-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Skriptoteket replaces its local copies of the shared dense components with the
package versions through sync.

- Map `dense-tool-primitives`, `ui-dense-action-button`,
  `ui-dense-icon-button`, `ui-dense-status-pill`, `ui-segmented-toggle`,
  `system-message`, `toast-host` and `vue-barrel` to paths under
  `frontend/apps/skriptoteket/src/components/ui/`, replacing the local files,
  then run the sync.
- Components the package does not export stay local and are exported from a
  local barrel that re-exports the package barrel.
- SystemMessage call sites rename `variant` to `tone` and `error` to
  `failure`; dismissible messages use the package's dismiss and v-model
  support.
- A local ToastHost wrapper, modelled on HuleEdu's `HumanCJToastHost.vue`,
  passes `useToastStore()` toasts to the package ToastHost and handles dismiss;
  it replaces `<ToastHost />` in `App.vue`. The store and `useToast()` call
  sites stay unchanged.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md` (D9-D12).
- Dependency: TASK-SKRIPT-40-01-01.

## Core Vertical And Performance

The planner share panel renders the package action button in the `secondary`
tone with the busy spinner, a modal renders on the modal surface, and a toast
and a dismissible system message render from the package. The equal-width
toggle measures once per resize, as today.

## Validation

- A second sync changes no file; the validate command passes.
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches: planner toolbar and share panel, segmented toggles, a
  system message and a toast.

## Stop Conditions

- Stop if a package component lacks a prop a Skriptoteket call site needs;
  that is a missing promotion for skill-repository, not a local patch.

## Decided Contract Terms

| ID  | Decided contract term                                                                  |
| --- | -------------------------------------------------------------------------------------- |
| D1  | The seven dense and message components and the Vue barrel are adopted through sync.    |
| D2  | SystemMessage call sites use the package `tone` API.                                  |
| D3  | ToastHost is fed by a local wrapper around the unchanged toast store.                 |
| D4  | Non-package components stay local behind a local barrel that re-exports the package.  |
