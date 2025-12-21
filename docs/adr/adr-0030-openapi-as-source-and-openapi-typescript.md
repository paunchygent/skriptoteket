---
type: adr
id: ADR-0030
title: "OpenAPI as the API source of truth + generated TypeScript types"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-21
links: ["ADR-0027", "PRD-spa-frontend-v0.1"]
---

## Context

A full SPA increases the surface area of frontend ↔ backend contracts.
Hand-written TypeScript DTOs drift over time, especially as endpoints evolve and authorization/validation rules change.

FastAPI already provides an OpenAPI schema for documented routes.

## Decision

- Treat the backend OpenAPI schema as the **single source of truth** for API contracts.
- Generate TypeScript types via `openapi-typescript` and import generated types in the SPA.
- Add a lightweight “regen types” workflow that runs locally and in CI.

Authentication and authorization remain cookie-session based (ADR-0009):

- SPA sends `credentials: include`.
- Mutating requests include CSRF headers validated server-side.
- Backend returns consistent 401/403 responses; the SPA handles session expiry with a controlled re-login flow.

## Consequences

- Reduced contract drift between SPA and backend.
- OpenAPI quality becomes user-facing engineering hygiene (accurate response models, consistent error shapes).
- The frontend build becomes coupled to the backend schema (mitigate with stable versioning under `/api/v1`).
