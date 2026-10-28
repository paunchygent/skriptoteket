---
type: task
id: TASK-SKRIPT-REP-0019
title: 'ST-07-07: HTTP route dependency cutover off hybrid Dishka inject'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-REP-0019#closeout'
task_kind: repository
acceptance_criteria:
  - Given HTTP routes currently rely on `@inject` from `dishka_compat.py`, when this slice ships, then HTTP route dependency resolution uses the public FastAPI adapter pattern introduced in `PR-0162`.
  - Given route modules are migrated, when this slice ships, then HTTP handlers no longer depend on synthetic `___dishka_request` / `___dishka_websocket` kwargs.
  - Given OpenAPI and runtime proof are rerun, when this slice is verified, then the migrated HTTP routes keep their documented request/response contracts.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

## Contract Inputs

The source record did not define a separate section for this package heading.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Context

### Context

Even if observability is fixed first, the broader web layer still depends on the same hybrid
compatibility path across a large number of HTTP handlers. Leaving that in place keeps the
production risk alive.

Migrate the HTTP web layer off the hybrid injection decorator and onto the supported public FastAPI
adapter pattern.

### Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

### Story Contract Slice

Migrate the HTTP web layer off the hybrid injection decorator and onto the supported public FastAPI
adapter pattern.

### Contract Inputs

- Story parent: [ST-07-07](../stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md)
- Foundation slice: [PR-0162](pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md)

### Plan

1. Classify the affected HTTP routes and auth dependencies that currently use `@inject` without an
   explicit request context.
2. Migrate them tranche-by-tranche to FastAPI `Depends` helpers backed by
   `request.state.dishka_container`.
3. Keep response models, status codes, and auth semantics unchanged while the DI mechanism changes.
4. Extend web/openapi coverage so the migration is guarded by tests instead of only by smoke.

### Implementation Steps

1. Classify the affected HTTP routes and auth dependencies that currently use `@inject` without an
   explicit request context.
2. Migrate them tranche-by-tranche to FastAPI `Depends` helpers backed by
   `request.state.dishka_container`.
3. Keep response models, status codes, and auth semantics unchanged while the DI mechanism changes.
4. Extend web/openapi coverage so the migration is guarded by tests instead of only by smoke.

### Proof

- targeted pytest for migrated web modules
- `tests/test_openapi_contracts.py`
- live API smoke against representative public/auth/admin/planner routes
- `pdm run docs-validate`

### Validation

- targeted pytest for migrated web modules
- `tests/test_openapi_contracts.py`
- live API smoke against representative public/auth/admin/planner routes
- `pdm run docs-validate`

### Stop Conditions

- Roll back the affected route tranche together if the public adapter introduces contract drift.
- Keep `PR-0162` in place so observability remains on the supported path even if wider migration
  needs iteration.

### Lessons Learned

No separate material is recorded in the source snapshot.

### Notes

### Problem

Even if observability is fixed first, the broader web layer still depends on the same hybrid
compatibility path across a large number of HTTP handlers. Leaving that in place keeps the
production risk alive.

### Goal

Migrate the HTTP web layer off the hybrid injection decorator and onto the supported public FastAPI
adapter pattern.

### Non-goals

- Websocket migration.
- Provider/container topology redesign.
- Rewriting unrelated application/domain code.

### Implementation plan

1. Classify the affected HTTP routes and auth dependencies that currently use `@inject` without an
   explicit request context.
2. Migrate them tranche-by-tranche to FastAPI `Depends` helpers backed by
   `request.state.dishka_container`.
3. Keep response models, status codes, and auth semantics unchanged while the DI mechanism changes.
4. Extend web/openapi coverage so the migration is guarded by tests instead of only by smoke.

### Test plan

- targeted pytest for migrated web modules
- `tests/test_openapi_contracts.py`
- live API smoke against representative public/auth/admin/planner routes
- `pdm run docs-validate`

### Rollback plan

- Roll back the affected route tranche together if the public adapter introduces contract drift.
- Keep `PR-0162` in place so observability remains on the supported path even if wider migration
  needs iteration.

### References

- Story parent: [ST-07-07](../stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md)
- Foundation slice: [PR-0162](pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md)

### Plan Document Review

No separate material is recorded in the source snapshot.

### Implementation Review

No separate material is recorded in the source snapshot.

## Impact And Escalation

The migrated source records no separate statement for this section.

## Decision And Assumption Ledger

The migrated source records no separate statement for this section.

## Plan

The migrated source records no separate statement for this section.

## Implementation Steps

The migrated source records no separate statement for this section.

## Proof

The migrated source records no separate statement for this section.

## Validation

The migrated source records no separate statement for this section.

## Stop Conditions

The migrated source records no separate statement for this section.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

The migrated source records no separate statement for this section.

## Notes

The migrated source records no separate statement for this section.

## Readiness

The migrated source records no separate statement for this section.

## Closeout

The migrated source records no separate statement for this section.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

HTTP route and auth-dependency injection moved off the `dishka_compat.py` `@inject` decorator onto `FromDishka` (FastAPI `Depends` on `request.state.dishka_container`) in 1743db254 on 2026-03-29; `src/skriptoteket/web/dishka_compat.py` is deleted and `@inject`, `___dishka_request` and `___dishka_websocket` no longer occur in `src` or `tests`. 57 web modules use `src/skriptoteket/web/dishka_dependencies.py`, and `tests/unit/web/test_openapi_contracts.py` guards the contracts. A per-route live smoke over public/auth/admin/planner routes is not recorded separately; the Hemma `/healthz` and `/metrics` proof is.
