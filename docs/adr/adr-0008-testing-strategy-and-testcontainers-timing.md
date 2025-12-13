---
type: adr
id: ADR-0008
title: "Testing strategy and when to introduce Testcontainers"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

We want high confidence without premature infrastructure complexity. Early in the project, the priority is defining domain boundaries and repository interfaces correctly.

## Decision

- Start with unit tests around domain/application logic using protocol-based fakes/mocks.
- Add integration tests once PostgreSQL repositories and models exist.
- Introduce Testcontainers only after the database layer is in place and we have meaningful repository/integration behavior to validate.

## Consequences

- Tests stay fast and focused early, while still leaving a clear path to full DB-backed integration coverage later.
