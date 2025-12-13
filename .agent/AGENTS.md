# Architecture Reference

Rules: `.agent/rules/000-rule-index.md`

## Golden Rules

- **No vibe-coding** - Every change follows established patterns (010)
- **Protocol-first** - All dependencies via `typing.Protocol` (042)
- **<500 LoC** - Hard limit per file (010)
- **Understand first** - Read rules before implementing (010)

## Layer Structure (020)

```text
src/
├── api/           # JSON HTTP (thin, optional): routers, DTOs, validation
├── web/           # Server-rendered UI (thin): pages, templates, HTMX partials
├── domain/        # Business logic (pure): services, models, events
├── infrastructure/# External: repositories, clients, publishers
└── workers/       # Kafka consumers
```

- Domain has no external dependencies
- Web/API depend on domain protocols
- Infrastructure implements domain protocols

## DI Patterns (042)

- Define all deps in `protocols.py`
- Dishka container in `di.py`
- `Scope.APP`: engine, sessionmaker, publishers (singletons)
- `Scope.REQUEST`: session, unit-of-work, repos, services (per-request)
- Unit of Work controls commit/rollback; repositories do not commit

## Events (030)

- Kafka is deferred in v0.1; if/when introduced:
  - All messages use `EventEnvelope[T]`
  - Transactional outbox pattern for reliability
  - Correlation ID in every message

## Errors (048)

- `DomainError(code, message, details)` (no HTTP concerns)
- `ErrorCode` enum for all error types
- Correlation ID is attached/logged at the boundary (middleware)

## Testing (070)

- Mock protocols: `AsyncMock(spec=Protocol)`
- No conftest magic - explicit fixture imports
- Extract pure `_impl` functions for unit tests
- <500 LoC per test file

## Forbidden

- Business logic in API layer
- Raw SQL (use SQLAlchemy ORM)
- `try/except pass`
- Relative imports across modules
- Mocking implementations (mock protocols)
- `@patch` decorator (use DI)
