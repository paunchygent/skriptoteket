---
type: pr
id: PR-0334
title: "ST-21-04 Correction-session API and generated types"
status: blocked
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - backend
  - frontend
  - openapi
  - conversion-hub
  - exam-converter
  - teacher-corrections
dependencies:
  - "ADR-0087"
  - "PR-0333"
acceptance_criteria:
  - "Given PR-0333 has landed, when authenticated correction-session routes are added, then they expose owner-scoped read, upsert/replace, and delete/revert behavior for the current active set."
  - "Given a write request omits or sends a stale expected session version, when the handler runs, then the API returns `409 Conflict` behavior without mutating the active set."
  - "Given source binding, item binding, unsupported kind, or incompatible active-intent validation fails, when the handler runs, then the API returns a structured domain error and does not call Sir Convert."
  - "Given the OpenAPI schema is exported, when frontend types are regenerated, then the generated client types expose the correction-session request/response, conflict, and current-set readback shapes."
  - "Given a teacher accesses another user's job/session, when the API request is made, then owner scoping rejects the request before returning correction state."
---

# PR-0334: ST-21-04 Correction-Session API And Generated Types

## Problem

The backend aggregate from `PR-0333` needs an authenticated application/API
surface before the frontend can commit or read back persisted correction truth.
The route contract must preserve the aggregate invariants and expose conflict
semantics clearly enough for generated frontend types to be useful.

## Scope

- Add authenticated correction-session application handlers and FastAPI routes.
- Preserve owner scoping, expected-version writes, replace/delete semantics,
  and source-binding validation at the application boundary.
- Export OpenAPI and regenerate Skriptoteket frontend API types.
- Add focused API tests for owner scoping, conflict behavior, validation
  failures, and readback.

## Non-Goals

- No Sir Convert replay orchestration.
- No frontend UI wiring beyond generated types/client surface.
- No artifact readiness or download behavior.
- No matching answer-key support.

## Test Plan

- Focused API tests for read/upsert/delete, `409 Conflict`, owner scoping, and
  hard validation failures.
- OpenAPI export and generated frontend type checks.
- Backend lint/typecheck and focused route/application tests.
