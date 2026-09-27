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

Migrate every applicable Skriptoteket icon use to shared UiGlyph or UiSymbol
by meaning. TASK-SKILL-REP-0187 inventories current uses, promotes missing
meanings in a separate release, publishes the mapping and syncs HuleEdu.
Skriptoteket refreshes the glyph exports already adopted in Story 1, migrates
call sites and removes `lucide-vue-next`. Custom icons remain only where the
mapping explicitly records that no shared meaning fits.

The prior counts of 66 Lucide icons and 68 custom components are discovery
snapshots, not scope limits. Inventory current direct imports, custom
components, re-exports, type references and dynamic component uses. Do not
promise per-meaning tree-shaking or an unaccepted zero-growth bundle limit.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D13-D17 and admitted D20/D23-D24.
- ST-SKRIPT-40-01 done with complete runtime dependencies; TASK-SKILL-REP-0187 merged release, mapping and HuleEdu proof.
- EPIC-SKRIPT-40 review R1/R5/R6 and its admitted repair.

## Tasks

| Order | Task | Outcome |
| --- | --- | --- |
| 0 | TASK-SKILL-REP-0187 | Current use-to-meaning mapping, missing meanings released, HuleEdu synced and checked. |
| 1 | TASK-SKRIPT-40-02-01 | Existing glyph adoption refreshed, all mapped uses migrated, old Lucide dependency removed. |

## Verification

- No application source imports `lucide-vue-next`; its application dependency and obsolete resolved dependency entries are removed.
- Every current icon use is covered by a shared meaning or an explicit local classification. Local exceptions must not retain the removed peer.
- `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build` and shared design-system validation pass; clean-state repeat sync changes no file.
- Retain comparable production build reports as risk evidence, without inventing a numerical acceptance limit.
- Walk every changed-icon screen on Hemma staging using the HuleEdu browser-session helpers/preflight.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Icons migrate by meaning and missing meanings are promoted. Source: retained D14. |
| D2 | Explicitly classified custom icons remain where no shared meaning fits. Source: retained D14. |
| D3 | Vocabulary promotions ship after mapping in their own release; runtime/peer adoption already occurred in Story 1. Source: retained D15/D20; R1. |
| D4 | Frontend, shared-validator and touched-screen staging proof remain required. Source: retained D16. |
| D5 | No per-meaning bundling guarantee or zero-growth acceptance limit is inferred from individual imports. Source: retained D23; R5. |
