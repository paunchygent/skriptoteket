---
id: "000-rule-index"
type: "standards"
created: 2025-12-13
scope: "all"
---

# Monolith Architecture Rules: Index

**MUST** adhere to these rules for all development. These rules define a FastAPI monolithic application with PostgreSQL (Kafka is optional/future), following DDD and Clean Architecture principles.

## Core Principles
- [010-foundational-principles.md](010-foundational-principles.md): Non-negotiable tenets and mindset
- [020-monolith-architecture.md](020-monolith-architecture.md): Layer structure and boundaries

## Communication & Events
- [030-event-driven-patterns.md](030-event-driven-patterns.md): Eventing patterns (apply only if/when Kafka is introduced)

## Implementation Standards
- [040-fastapi-blueprint.md](040-fastapi-blueprint.md): HTTP service patterns, routers, validation
- [042-async-di-patterns.md](042-async-di-patterns.md): Protocols, Dishka DI, async patterns
- [048-error-handling.md](048-error-handling.md): Structured errors, correlation IDs
- [050-python-standards.md](050-python-standards.md): Style, typing, formatting, file limits
- [053-sqlalchemy-patterns.md](053-sqlalchemy-patterns.md): Repository pattern, session management
- [060-docker-and-compose.md](060-docker-and-compose.md): Docker/Compose workflow (dev/prod), deprecated keys, secrets

## Quality Assurance
- [070-testing-standards.md](070-testing-standards.md): Testing strategies, protocol mocks, fixtures

---

**Directive Keywords**: `MUST`, `SHALL`, `FORBIDDEN`, `REQUIRED` are non-negotiable. Other phrasing indicates best practices.
