---
type: reference
id: REF-SKRIPT-GENERAL-architecture-and-coding-principles
title: Architecture and coding principles
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-architecture
summary: Architecture and coding principles
---

## Overview

No separate source material was recorded for this section.

## Facts And Semantics

### Source: Layers and responsibilities

- **Domain**: entities/value objects, domain services, domain errors, invariants.
- **Application**: commands/queries + handlers; orchestration; transaction boundaries via Unit of Work; depends on protocols.
- **Infrastructure**: PostgreSQL repositories, migrations, external clients; implements application/domain protocols.
- **Web**: FastAPI routers, request/response schemas, dependency wiring; no business rules.

### Source: Data models (dataclasses vs Pydantic)

- **Pydantic**: any model that crosses a boundary (between domains/layers, shared contracts, command/query DTOs, repository interface I/O).
- **`dataclasses`**: internal, single-domain structures only (do not leak across boundaries).

### Source: PostgreSQL repositories

- Define repository interfaces as `typing.Protocol` in domain/application.
- Provide async implementations in infrastructure (PostgreSQL).
- Keep SQL/ORM details out of domain/application.

### Source: Dependency injection

- Use an explicit **composition root** (web startup) to bind protocols → implementations.
- Prefer constructor injection; avoid hidden globals/singletons.

## Decisions And Interpretation

### Source: Principles (non-negotiable)

- DDD + Clean Architecture: business logic is framework-agnostic.
- Dependency rule: `domain` has **zero** dependencies on `web` or `infrastructure`.
- SRP everywhere: prefer small modules; avoid “god” classes/services.
- File size: keep modules < ~400–500 LOC; split by responsibility.
- Async-first: use `async def` end-to-end for I/O, especially DB access.
- No legacy support / compatibility shims: do the full refactor and delete old paths instead.

### Source: Command handler pattern (recommended)

- One handler per use-case (e.g., `CreateTool`, `RunTool`).
- Handler input/output are **Pydantic models** when crossing domain boundaries (e.g., web → application, application → other domain, events, shared contracts).
- Handler depends on protocols (e.g., `ToolRepository`, `UnitOfWork`, `Clock`, `IdGenerator`).
