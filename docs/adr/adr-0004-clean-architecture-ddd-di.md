---
type: adr
id: ADR-0004
title: "Architecture: DDD + Clean Architecture + DI (async, SRP)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

We want an MVP that stays maintainable as it grows: no “god modules”, clear responsibility boundaries, and testable business rules that do not depend on frameworks or infrastructure.

## Decision

Adopt **Domain-Driven Design** with **Clean Architecture** (dependency inversion):

- **Domain**: pure business rules (no FastAPI/DB/Pydantic imports).
- **Application**: use-cases as **command/query handlers**; depends on domain + protocols.
- **Infrastructure**: PostgreSQL repositories and external integrations implementing protocols.
- **Interface/Web**: FastAPI routes and I/O models; calls application handlers.
- **DI**: explicit composition root wires implementations to protocols; business logic depends only on abstractions.

Hard constraints:

- Prefer **SRP** modules; avoid monolith “service” objects.
- Keep files small (target < ~400–500 LOC per file).
- Cross-domain contracts use **Pydantic models**; `dataclasses` are for internal (single-domain) structures only.
- Async-first: handlers + repositories are `async` and avoid blocking work.
- Single container deployment: one Docker image runs Uvicorn.

## Consequences

- More up-front structure, but faster long-term change and clearer reviewability.
- Requires discipline: new features must respect the dependency direction and keep logic out of web/infra layers.
