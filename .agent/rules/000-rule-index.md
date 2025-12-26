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
- [045-huleedu-design-system.md](045-huleedu-design-system.md): HuleEdu design tokens, button hierarchy, components
- [048-error-handling.md](048-error-handling.md): Structured errors, correlation IDs
- [050-python-standards.md](050-python-standards.md): Style, typing, formatting, file limits
- [053-sqlalchemy-patterns.md](053-sqlalchemy-patterns.md): Repository pattern, session management
- [054-alembic-migrations.md](054-alembic-migrations.md): Migration workflow + idempotency testing
- [060-docker-and-compose.md](060-docker-and-compose.md): Docker/Compose workflow (dev/prod), deprecated keys, secrets

## Quality Assurance

- [070-testing-standards.md](070-testing-standards.md): Testing strategies, protocol mocks, fixtures
- [075-browser-automation.md](075-browser-automation.md): Playwright/Selenium patterns

## Operations

- [080-home-server-deployment.md](080-home-server-deployment.md): Home server deployment and operations
- [090-observability-index.md](090-observability-index.md): Observability standards (logging, metrics, tracing)
  - [091-structured-logging.md](091-structured-logging.md): Correlation IDs, JSON logs
  - [092-health-and-metrics.md](092-health-and-metrics.md): /healthz, Prometheus metrics
  - [093-distributed-tracing.md](093-distributed-tracing.md): OpenTelemetry, spans
  - [094-observability-infrastructure.md](094-observability-infrastructure.md): Stack deployment

## Documentation & Planning

- [096-review-workflow.md](096-review-workflow.md): EPIC/Story review workflow (REQUIRED before implementation)

---

**Directive Keywords**: `MUST`, `SHALL`, `FORBIDDEN`, `REQUIRED` are non-negotiable. Other phrasing indicates best practices.
