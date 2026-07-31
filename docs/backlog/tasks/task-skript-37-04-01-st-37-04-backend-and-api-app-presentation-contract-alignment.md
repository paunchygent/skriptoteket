---
type: task
id: TASK-SKRIPT-37-04-01
title: ST-37-04 backend and API app presentation contract alignment
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: blocked
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-37-04
task_kind: story
acceptance_criteria:
- Given a reviewed route-visible slice has proven the compatibility shell can no longer
  express the teacher-facing app model truthfully, when this slice runs, then backend/bootstrap
  or API contracts explicitly represent the required app-presentation split without
  breaking current authorized consumers.
- Given frontend consumers rely on generated contracts, when an API-visible change
  is introduced, then generated types, focused backend tests, focused frontend tests,
  and route-visible browser proof all move together.
- Given Sir Convert and HuleEdu boundaries are already defined elsewhere, when this
  slice closes, then it still does not change producer, Gateway, QTI, DOCX, or native
  exam/transcript ownership doctrine.
dependencies:
- REF-SKRIPT-PLAN-app-presentation-decomposition-and-naming-plan
---

## Context
### Problem
The current planning package does not assume a backend or API app-presentation
split is needed. `PR-0375` also keeps the first Document Converter backend/API
follow-up under the existing `documents.conversion_hub` technical app id. If
later route-visible or Document Converter work proves that assumption false,
the contract change must happen in this explicit slice rather than being
smuggled into frontend work.
### Review gate
`REV-PR-0369` must be approved before code implementation begins.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Story Contract Slice
### Goal
Reserve a separate reviewed slice for any real backend or API work required by
app-presentation decomposition.
### Non-goals
- No contract change unless `PR-0368`, `PR-0375`, or later reviewed
  route-visible/backend work documents a concrete incompatibility.
- No Sir Convert, HuleEdu, QTI, or DOCX contract change.
- No fake Document Converter route or host.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Plan
### Implementation plan
1. Start only if a reviewed route-visible or Document Converter follow-up closes
   with written evidence that truthful app presentation cannot be maintained on
   the current compatibility bootstrap/API shape.
2. Define the smallest possible backend/bootstrap or API contract adjustment:
   metadata split, capability split, or app-detail decomposition.
3. Update generated frontend consumers and keep app-state ownership doctrine
   aligned with
   [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md).
4. Stop and re-plan if the proposal drifts into Sir Convert producer/Gateway
   work or into implementation of a still-hypothetical Document Converter app.
### Test plan
- Red first:
  targeted backend or API contract tests named by the chosen implementation
  path.
- Green:
  rerun the same targeted backend tests plus any changed frontend consumer
  tests.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- Regenerate frontend API types if the contract surface changes.
- Route-visible browser proof through the HuleEdu browser-session ceremony if a
  UI consumer changes.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
### Rollback plan
Restore the prior contract surface and keep the route-visible work on the
compatibility path while re-planning the decomposition.

## Implementation Steps
The source record did not define a separate section for this package heading.

## Proof
The source record did not define a separate section for this package heading.

## Validation
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Lessons Learned
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Implementation Review
The source record did not define a separate section for this package heading.
