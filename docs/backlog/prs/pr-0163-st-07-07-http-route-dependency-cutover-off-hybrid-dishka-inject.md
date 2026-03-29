---
type: pr
id: PR-0163
title: "ST-07-07: HTTP route dependency cutover off hybrid Dishka inject"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-07-07"
tags: ["backend", "fastapi", "dishka", "routes", "production"]
dependencies:
  - "PR-0162"
acceptance_criteria:
  - "Given HTTP routes currently rely on `@inject` from `dishka_compat.py`, when this slice ships, then HTTP route dependency resolution uses the public FastAPI adapter pattern introduced in `PR-0162`."
  - "Given route modules are migrated, when this slice ships, then HTTP handlers no longer depend on synthetic `___dishka_request` / `___dishka_websocket` kwargs."
  - "Given OpenAPI and runtime proof are rerun, when this slice is verified, then the migrated HTTP routes keep their documented request/response contracts."
---

## Problem

Even if observability is fixed first, the broader web layer still depends on the same hybrid
compatibility path across a large number of HTTP handlers. Leaving that in place keeps the
production risk alive.

## Goal

Migrate the HTTP web layer off the hybrid injection decorator and onto the supported public FastAPI
adapter pattern.

## Non-goals

- Websocket migration.
- Provider/container topology redesign.
- Rewriting unrelated application/domain code.

## Implementation plan

1. Classify the affected HTTP routes and auth dependencies that currently use `@inject` without an
   explicit request context.
2. Migrate them tranche-by-tranche to FastAPI `Depends` helpers backed by
   `request.state.dishka_container`.
3. Keep response models, status codes, and auth semantics unchanged while the DI mechanism changes.
4. Extend web/openapi coverage so the migration is guarded by tests instead of only by smoke.

## Test plan

- targeted pytest for migrated web modules
- `tests/test_openapi_contracts.py`
- live API smoke against representative public/auth/admin/planner routes
- `pdm run docs-validate`

## Rollback plan

- Roll back the affected route tranche together if the public adapter introduces contract drift.
- Keep `PR-0162` in place so observability remains on the supported path even if wider migration
  needs iteration.

## References

- Story parent: [ST-07-07](../stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md)
- Foundation slice: [PR-0162](pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md)
