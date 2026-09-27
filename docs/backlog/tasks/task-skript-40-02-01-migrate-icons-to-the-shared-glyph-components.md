---
type: task
id: TASK-SKRIPT-40-02-01
title: Migrate icons to the shared glyph components
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
- Every Skriptoteket icon renders through UiGlyph or UiSymbol by meaning, custom Icon components remain only where the mapping records no shared meaning, and lucide-vue-next is removed
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
dependencies:
- TASK-SKRIPT-40-01-03
- TASK-SKILL-REP-0187
story: ST-SKRIPT-40-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Skriptoteket adopts `ui-glyphs`, `ui-glyph` and `ui-symbol` through sync and
migrates every icon to them by meaning, using the mapping delivered by
skill-repository TASK-SKILL-REP-0187.

- Replace each `lucide-vue-next` import and each custom `Icon*.vue` use that
  has a shared meaning with `UiGlyph` or `UiSymbol`.
- Keep a custom icon component only where the mapping records no shared
  meaning.
- Remove `lucide-vue-next` from `frontend/apps/skriptoteket/package.json` and
  add the package's `@lucide/vue` peer through the frontend catalog.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md` (D13-D14).
- Prerequisites: ST-SKRIPT-40-01 done; TASK-SKILL-REP-0187 merged.

## Core Vertical And Performance

Every screen renders its icons from the shared glyph components. Icon
components are imported per meaning, so bundle size must not grow beyond the
current `lucide-vue-next` usage.

## Validation

- `rg lucide-vue-next frontend/apps/skriptoteket` finds nothing.
- A second sync changes no file; the validate command passes.
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches: every screen whose icons changed.

## Stop Conditions

- Stop if an icon has no meaning in the released mapping; add it to the
  package, not locally.

## Decided Contract Terms

| ID  | Decided contract term                                                            |
| --- | -------------------------------------------------------------------------------- |
| D1  | Icons migrate by meaning to UiGlyph or UiSymbol.                                 |
| D2  | Custom icons remain only where the mapping records no shared meaning.            |
| D3  | `lucide-vue-next` is removed; `@lucide/vue` comes through the frontend catalog.  |
