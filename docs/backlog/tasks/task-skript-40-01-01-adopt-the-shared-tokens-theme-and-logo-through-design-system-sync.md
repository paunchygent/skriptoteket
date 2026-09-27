---
type: task
id: TASK-SKRIPT-40-01-01
title: Adopt the shared tokens, theme and logo through design-system sync
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
- Running repository-governance-frontend-catalog design-system sync against Skriptoteket writes the package tokens, Tailwind theme and horizontal logo to their current Skriptoteket paths as named in the root design-system-map.json, with every other export null, and Skriptoteket's validate command passes
- Skriptoteket docs name the sync command instead of hand copying, and the unused mirror manifest.schema.json is gone
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
dependencies:
- TASK-SKILL-REP-0186
story: ST-SKRIPT-40-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Skriptoteket adopts `design-system sync` for the tokens, Tailwind theme and
horizontal logo of the package version released by TASK-SKILL-REP-0186.

- Add `design-system-map.json` at the repository root: package
  `huleedu-integrated`, mirror
  `frontend/apps/skriptoteket/src/design-system/huleedu-integrated`, and all
  export ids. `tokens` maps to
  `src/skriptoteket/web/static/css/huleedu-design-tokens.css`,
  `tailwind-theme` to `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`,
  `skriptoteket-logo-horizontal` to
  `frontend/apps/skriptoteket/public/logo-horizontal.svg`; every other export
  is `null`.
- Add `[tool.repository-governance.design-system]` to `pyproject.toml` with
  `map` and a `validate-command` that runs a new pdm script wrapping the shared
  `design-system validate`.
- Add a pre-commit hook running that script on the map, the mirror, the adopted
  targets, `pyproject.toml` and the hook configuration.
- Run a real sync from the skill-repository main checkout. The local modal
  surface tokens now come from the package; the palette moves to the package's
  current values.
- Delete the unused mirror `manifest.schema.json`.
- Replace the hand-copy steps in the frontend design-system codemap reference
  with the sync command.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`; discovery `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/discovery/design-system-adoption.md`.
- Prerequisite: skill-repository TASK-SKILL-REP-0186 merged.
- Continues canceled TASK-SKRIPT-REP-0033.

## Core Vertical And Performance

One sync run writes the three adopted files, the mirror metadata and the map,
then the validate command passes. No runtime performance concern: the change is
static CSS and SVG.

## Validation

- The sync exits 0 and a second sync changes no file.
- `tests/unit/governance/test_repository_governance_bootstrap.py` passes with
  the design-system facts.
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches: home, tool list, Klassrumskartan planner and a modal.

## Stop Conditions

- Stop if the sync refuses because a target has uncommitted changes or the
  source package does not match its digests.
- Stop if an adopted token removes a name Skriptoteket still uses.

## Decided Contract Terms

| ID  | Decided contract term                                                                         |
| --- | --------------------------------------------------------------------------------------------- |
| D1  | Adopt tokens, tailwind-theme and skriptoteket-logo-horizontal; all other exports are `null`.  |
| D2  | Adopted files keep their current paths; the map sits at the repository root.                  |
| D3  | The validate command is a pdm script around the shared validate, run by a pre-commit hook.     |
| D4  | The unused mirror `manifest.schema.json` is deleted.                                          |
| D5  | The codemap reference names the sync command instead of hand copying.                        |
