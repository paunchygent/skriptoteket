---
type: adr
id: ADR-SKRIPT-0030
title: OpenAPI as the API source of truth + generated TypeScript types
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0030
---

## Context

### Source: Context

A full SPA increases the surface area of frontend ↔ backend contracts.
Hand-written TypeScript DTOs drift over time, especially as endpoints evolve and authorization/validation rules change.

FastAPI already provides an OpenAPI schema for documented routes.

## Decision

### Source: Decision

- Treat the backend OpenAPI schema as the **single source of truth** for API contracts.
- Generate TypeScript types via `openapi-typescript` and import generated types in the SPA.
- Add a lightweight “regen types” workflow that runs locally and in CI.

Authentication and authorization remain cookie-session based (ADR-SKRIPT-0009):

- SPA sends `credentials: include`.
- Mutating requests include CSRF headers validated server-side.
- Backend returns consistent 401/403 responses; the SPA handles session expiry with a controlled re-login flow.

## Non-Decisions

The source does not authorize additional alternatives or scope beyond the decision above.

## Consequences

### Source: Consequences

- Reduced contract drift between SPA and backend.
- OpenAPI quality becomes user-facing engineering hygiene (accurate response models, consistent error shapes).
- The frontend build becomes coupled to the backend schema (mitigate with stable versioning under `/api/v1`).
