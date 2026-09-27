---
type: story
id: ST-SKRIPT-40-02
title: Converge icons onto the shared glyph vocabulary
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
- Every Skriptoteket icon renders through the shared UiGlyph or UiSymbol by meaning, custom Icon components remain only where no shared meaning fits, and lucide-vue-next is removed
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Every icon in Skriptoteket renders through the shared `UiGlyph` or `UiSymbol`
components by meaning. A skill-repository task first maps the 66 Lucide icons
Skriptoteket imports and its 68 custom `Icon*.vue` components to meanings,
promotes the meanings the package lacks in its own release, and syncs HuleEdu.
Skriptoteket then adopts ui-glyphs, ui-glyph and ui-symbol, migrates every call
site and removes `lucide-vue-next`. Custom icons stay local only where no
shared meaning fits.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md` (D13-D17).
- Prerequisites: ST-SKRIPT-40-01 done; skill-repository TASK-SKILL-REP-0187.

## Tasks

| Order | Task                 | Outcome                                                                     |
| ----- | -------------------- | --------------------------------------------------------------------------- |
| 0     | TASK-SKILL-REP-0187  | Icon-to-meaning mapping; missing meanings released; HuleEdu synced          |
| 1     | TASK-SKRIPT-40-02-01 | Glyph exports adopted; call sites migrated; `lucide-vue-next` removed       |

## Verification

- No Skriptoteket source imports `lucide-vue-next`, and the dependency is gone
  from `frontend/apps/skriptoteket/package.json`.
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, walking every screen whose icons changed.

## Decided Contract Terms

| ID  | Decided contract term                                                                               |
| --- | --------------------------------------------------------------------------------------------------- |
| D1  | Icons migrate by meaning to UiGlyph or UiSymbol; missing meanings are promoted into the package.    |
| D2  | Custom `Icon*.vue` components stay local only where no shared meaning fits.                          |
| D3  | The glyph promotions ship in their own package release after the mapping.                           |
| D4  | Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches.                                                                                      |
