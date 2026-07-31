---
type: adr
id: ADR-SKRIPT-0008
title: Testing strategy and when to introduce Testcontainers
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0008
---

## Context
We want high confidence without premature infrastructure complexity. Early in the project, the priority is defining domain boundaries and repository interfaces correctly.

## Decision
- Start with unit tests around domain/application logic using protocol-based fakes/mocks.
- Add integration tests once PostgreSQL repositories and models exist.
- Introduce Testcontainers only after the database layer is in place and we have meaningful repository/integration behavior to validate.

## Non-Decisions
The source record did not define a separate section for this package heading.

## Consequences
- Tests stay fast and focused early, while still leaving a clear path to full DB-backed integration coverage later.
