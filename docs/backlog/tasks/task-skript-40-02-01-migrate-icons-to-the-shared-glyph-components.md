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

Refresh the glyph exports already adopted in Story 1 through sync from the
0187 release. Use its published current-use mapping to migrate every applicable
icon to UiGlyph or UiSymbol by meaning. Keep the established shared subtree
and released catalog peer; this task does not first introduce @lucide/vue.

- Re-enumerate direct imports, custom Icon components, re-exports and dynamic uses against the released mapping; prior inventory counts are not limits.
- Replace each lucide-vue-next use and each custom icon use with a shared meaning where one fits. Preserve accessible names, decorative status and control meaning.
- Keep a custom icon only where the mapping explicitly classifies it local because no shared meaning fits. Such an exception must not retain lucide-vue-next.
- Remove the old dependency from the application manifest and reconcile the frontend lock. Preserve the catalog-managed released @lucide/vue peer.
- If export ids and targets are unchanged, do not pre-edit map version: let sync update it with the hook active. Otherwise use the admitted 01-01 map-preparation checkpoint sequence. Parent commits the validated result before repeat-sync proof.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D13-D16 and admitted D20/D23-D24.
- ST-SKRIPT-40-01 done; TASK-SKILL-REP-0187 merged with published mapping, release identity and HuleEdu proof.
- EPIC-SKRIPT-40 review R1/R5/R6 and local-exception clarification.

## Core Vertical And Performance

Every changed screen renders its mapped icons through the shared components;
explicit local exceptions remain functional without the old peer. UI_GLYPHS
is an eager runtime lookup table, so per-meaning tree-shaking is not promised.

Retain comparable before/after `pdm run fe-build` production reports with exact
SHAs, toolchain, lockfiles and unchanged build mode/configuration. Record raw
and available compressed chunk sizes, distinguishing initial and lazy chunks,
and compare Story-2 baseline to final migration separately from Story-1 costs.
These reports disclose risk; no zero-growth or other numerical acceptance
limit is authorized. A requested hard limit needs a separately closed user
metric, baseline and budget before becoming a gate.

## Validation

- Search application source/manifests for lucide-vue-next; require no remaining import or dependency and no obsolete resolved entry for it in the frontend lock. Historical prose is not runtime dependency evidence.
- Verify current icon inventory coverage against the published shared/local classification, including dynamic uses and accessible labels.
- Real sync and shared validation pass; parent-committed protected paths are clean; the repeat sync exits 0 with no diff. Automatic hook enforcement remains active at delivery.
- `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build` and `pdm run design-system-validate` pass. Retain the comparable production-build reports.
- Walk every changed-icon screen on Hemma staging through the governed HuleEdu browser-session helpers/preflight.

## Stop Conditions

- Stop on an unclassified use, a missing released shared meaning, or a mapping/code mismatch; route meaning promotion upstream. An explicit local classification is permitted and is not itself a stop condition.
- Stop if a local exception still requires the removed peer, or a required validation/checkpoint fails. Do not redesign the package to satisfy an invented bundle guarantee.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Migrate applicable icons by meaning to UiGlyph or UiSymbol. Source: retained D14. |
| D2 | Explicitly classified no-shared-meaning custom icons may remain local. Source: retained D14. |
| D3 | Remove lucide-vue-next; the released catalog peer was installed in Story 1. Source: retained D13/D20; R1. |
| D4 | Runtime-table retention is a measured risk, not a per-meaning or zero-growth guarantee. Source: retained D23; R5. |
| D5 | Repeat-sync proof starts from a clean committed validated result. Source: retained D24; R6. |
